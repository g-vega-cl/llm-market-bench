"""Weekly Autoresearch Task for Daily Stock Picker Arena (3 Up, 3 Down).

Runs weekly on Sunday at 18:00 ET (0 22 * * SUN). Evaluates the rolling 5-session
performance for each model track (DeepSeek Flash, MiniMax-M3.1-Flash, GPT Luna) against
a normalized ratchet hurdle:
Score = 0.50 * Directional Hit Rate + 0.40 * Normalized L/S Alpha + 0.10 * Conviction Norm.
Executes independent 1-in-6 stochastic cold-starts, synthesizes prompt mutations,
and deploys winning variants to prompt_experiments.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from core.config import (
    DEEPSEEK_FLASH_MODEL,
    MINIMAX_MODEL,
    OPENAI_MODEL,
    logger,
)
from core.conviction_scoring import conviction_bundle, select_baseline_candidate
from core.db import get_supabase_client
from core.llm.clients import close_client, get_deepseek_client
from core.llm.stock_picker_prompts import (
    STOCK_PICKER_CONSTRAINTS_FOOTER,
    STOCK_PICKER_CONSTRAINTS_HEADER,
    STOCK_PICKER_MUTABLE_STRATEGIES,
    split_stock_picker_prompt,
)

TARGET_TRACK_MODELS = [DEEPSEEK_FLASH_MODEL, MINIMAX_MODEL, OPENAI_MODEL]


class StockPickerMetaPromptResponse(BaseModel):
    new_strategy: str = Field(
        ...,
        description="The complete modified strategy and analytical reasoning instructions text for long/short stock picking",
    )
    hypothesis: str | None = Field(
        default=None,
        description="Concise testable hypothesis explaining why this strategy mutation should improve directional hit rate and L/S alpha.",
    )
    research_reasoning: str | None = Field(
        default=None,
        description="Analytical diagnosis of recent 5-session performance driving the prompt adjustment.",
    )
    research_insight: str | None = Field(
        default=None,
        description=(
            "A concise, durable strategic takeaway on equity momentum, catalyst selection, or long/short relative valuation "
            "to preserve in long-term memory for this model track."
        ),
    )


def sanitize_mutated_stock_strategy(raw_strategy: str) -> str:
    """Strip markdown code fences and guarantee the mutable section header is preserved."""
    cleaned = raw_strategy.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    header_marker = "=== LONG/SHORT RELATIVE SELECTION STRATEGY ==="
    if header_marker in cleaned:
        _, extracted, _ = split_stock_picker_prompt(
            STOCK_PICKER_CONSTRAINTS_HEADER + cleaned + STOCK_PICKER_CONSTRAINTS_FOOTER
        )
        return extracted.strip()

    return f"{header_marker}\n{cleaned}".strip()


def calculate_stock_picker_hurdle_score(
    hit_rate_pct: float,
    mean_ls_alpha_pct: float,
    conviction_norm: float = 50.0,
) -> float:
    """Calculate the normalized weekly ratchet score for stock picking.

    Maps L/S Alpha into [0, 100] centered at 50 (10 pts per 1.0% alpha),
    ensuring genuine 40% weighting across uniform [0, 100] metric scales.
    """
    normalized_alpha = max(0.0, min(100.0, 50.0 + (mean_ls_alpha_pct * 10.0)))
    score = (0.50 * hit_rate_pct) + (0.40 * normalized_alpha) + (0.10 * conviction_norm)
    return round(score, 4)


async def _resolve_active_stock_prompt(client: Any, model_name: str) -> tuple[str, str]:
    """Fetch or seed the active prompt for a stock picker model track."""
    res = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "STOCK_PICKER_PROMPT")
        .eq("track_id", model_name)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]["variant_tag"], res.data[0]["prompt_content"]

    base_res = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "STOCK_PICKER_PROMPT")
        .eq("track_id", model_name)
        .eq("status", "baseline")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if base_res.data:
        return base_res.data[0]["variant_tag"], base_res.data[0]["prompt_content"]

    # Seed initial baseline (idempotent upsert on variant_tag)
    today = datetime.now(UTC).date()
    week_end = today + timedelta(days=7)
    tag = f"stock-baseline-{model_name.lower().replace('/', '-').replace('~', '')}"
    full_prompt = STOCK_PICKER_CONSTRAINTS_HEADER + STOCK_PICKER_MUTABLE_STRATEGIES + STOCK_PICKER_CONSTRAINTS_FOOTER
    client.table("prompt_experiments").upsert(
        {
            "variant_tag": tag,
            "prompt_name": "STOCK_PICKER_PROMPT",
            "prompt_content": full_prompt,
            "track_id": model_name,
            "week_start": today.isoformat(),
            "week_end": week_end.isoformat(),
            "status": "baseline",
            "experiment_type": "baseline",
            "change_description": f"Initial seeded baseline for {model_name} stock picker track.",
        },
        on_conflict="variant_tag",
    ).execute()
    return tag, full_prompt


async def _optimize_stock_track(
    client: Any,
    model_name: str,
    days: int = 7,
    dry_run: bool = False,
    force_cold_start: bool | None = None,
) -> None:
    """Run optimization and ratchet update for a single model track."""
    logger.info(f"--- Running Stock Picker Autoresearch for track: {model_name} ---")

    # 1. Fetch evaluated baskets over lookback period
    cutoff = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
    baskets_res = (
        client.table("daily_stock_baskets")
        .select("*")
        .eq("model_name", model_name)
        .eq("status", "evaluated")
        .gte("target_date", cutoff)
        .execute()
    )
    baskets = baskets_res.data or []

    if not baskets:
        logger.info(f"Insufficient evaluated baskets for {model_name} in last {days} days. Skipping.")
        return

    # Calculate weekly metrics
    avg_hit_rate = sum(float(b.get("directional_hit_rate") or 0.0) for b in baskets) / len(baskets)
    avg_ls_alpha = sum(float(b.get("ls_spread_alpha_pct") or 0.0) for b in baskets) / len(baskets)

    # Fetch child picks to compute conviction points
    basket_ids = [b["id"] for b in baskets]
    picks_res = (
        client.table("daily_stock_picks")
        .select("confidence, is_hit")
        .in_("basket_id", basket_ids)
        .eq("status", "evaluated")
        .execute()
    )
    picks = picks_res.data or []
    scoring_records = [{"confidence": p.get("confidence"), "is_correct": p.get("is_hit")} for p in picks]
    conviction_metrics = conviction_bundle(scoring_records)
    conviction_norm = float(conviction_metrics.get("conviction_norm", 50.0))

    weekly_score = calculate_stock_picker_hurdle_score(avg_hit_rate, avg_ls_alpha, conviction_norm)
    logger.info(
        f"Track {model_name} 5-Session Performance: Hit Rate={avg_hit_rate:.1f}%, L/S Alpha={avg_ls_alpha:+.2f}%, Ratchet Score={weekly_score:.4f}"
    )

    parent_tag, current_prompt = await _resolve_active_stock_prompt(client, model_name)

    # 2. Check baseline ratchet
    all_variants = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "STOCK_PICKER_PROMPT")
        .eq("track_id", model_name)
        .execute()
        .data
        or []
    )
    normalized_variants: list[dict[str, Any]] = []
    for variant in all_variants:
        metrics = dict(variant.get("metrics") or {})
        if "score" not in metrics and isinstance(metrics.get("hurdle_score"), (int, float)):
            metrics["score"] = metrics["hurdle_score"]
        if "predictions_evaluated" not in metrics and isinstance(metrics.get("sample_baskets"), (int, float)):
            metrics["predictions_evaluated"] = metrics["sample_baskets"]
        normalized_variants.append({**variant, "metrics": metrics})

    best_baseline = select_baseline_candidate(normalized_variants, parent_tag, min_sample=1, min_traded=0)
    baseline_score = float(best_baseline[0]) if best_baseline is not None else 0.0
    baseline_variant = best_baseline[1] if best_baseline is not None else None

    is_baseline_beat = weekly_score >= baseline_score

    weekly_metrics = {
        "score": weekly_score,
        "hurdle_score": weekly_score,
        "hit_rate_pct": avg_hit_rate,
        "ls_spread_alpha_pct": avg_ls_alpha,
        "conviction_norm": conviction_norm,
        "sample_baskets": len(baskets),
        "predictions_evaluated": len(baskets),
    }

    if not dry_run:
        client.table("prompt_experiments").update({"metrics": weekly_metrics}).eq("variant_tag", parent_tag).execute()

    if is_baseline_beat:
        if not dry_run:
            logger.info(
                f"STOCK PICKER RATCHET ({model_name}): Weekly score {weekly_score:.4f} beat baseline {baseline_score:.4f}! Promoting {parent_tag} to baseline."
            )
            client.table("prompt_experiments").update({"status": "baseline"}).eq("variant_tag", parent_tag).execute()
            client.table("prompt_experiments").update({"status": "saved"}).in_("status", ["active", "baseline"]).eq(
                "prompt_name", "STOCK_PICKER_PROMPT"
            ).eq("track_id", model_name).neq("variant_tag", parent_tag).execute()
    elif baseline_variant is not None:
        logger.info(
            f"STOCK PICKER RATCHET ({model_name}): Weekly score {weekly_score:.4f} below baseline {baseline_score:.4f}. Discarding {parent_tag} and reverting to {baseline_variant.get('variant_tag')}."
        )
        if not dry_run:
            client.table("prompt_experiments").update({"status": "discarded"}).eq("variant_tag", parent_tag).execute()
        parent_tag = baseline_variant.get("variant_tag") or parent_tag
        current_prompt = baseline_variant.get("prompt_content") or current_prompt

    # 3. Stochastic 1-in-6 Cold Start Dice
    is_cold_start = (random.randint(1, 6) == 1) if force_cold_start is None else force_cold_start

    # 4. Meta-researcher synthesis
    header, mutable_strategy, footer = split_stock_picker_prompt(current_prompt)
    strategy_source = STOCK_PICKER_MUTABLE_STRATEGIES if is_cold_start else mutable_strategy

    system_instruction = (
        "You are an elite quantitative researcher optimizing long/short stock-picking strategies.\n"
        "Your task is to refine the mutable strategy instructions to maximize directional hit rate and Long/Short spread alpha.\n"
        "Focus on improving expectation-gap detection, pre-market volume confirmation, and multiple-compression short signals."
    )
    user_msg = (
        f"Track Model: {model_name}\n"
        f"Prior 5-Session Hit Rate: {avg_hit_rate:.1f}%\n"
        f"Prior 5-Session L/S Spread Alpha: {avg_ls_alpha:+.2f}%\n"
        f"Active Ratchet Score: {weekly_score:.4f} (Baseline: {baseline_score:.4f})\n\n"
        f"Current Strategy Section:\n{strategy_source}\n\n"
        "Provide a mutated, refined strategy section and a durable research insight."
    )

    ds_client = get_deepseek_client()
    try:
        meta_res: StockPickerMetaPromptResponse = await ds_client.chat.completions.create(
            model=DEEPSEEK_FLASH_MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_msg},
            ],
            response_model=StockPickerMetaPromptResponse,
            temperature=0.3,
        )
    finally:
        await close_client(ds_client, "deepseek")

    clean_strategy = sanitize_mutated_stock_strategy(meta_res.new_strategy)
    new_full_prompt = header + clean_strategy + footer
    new_tag = f"stock-v{uuid.uuid4().hex[:6]}-{model_name.lower().replace('/', '-').replace('~', '')}"

    if dry_run:
        logger.info(f"[DRY RUN] Would deploy variant {new_tag} for {model_name}. Insight: {meta_res.research_insight}")
        return

    # Demote current active to saved and insert new active variant
    client.table("prompt_experiments").update({"status": "saved"}).eq("prompt_name", "STOCK_PICKER_PROMPT").eq(
        "track_id", model_name
    ).eq("status", "active").execute()

    today = datetime.now(UTC).date()
    week_end = today + timedelta(days=7)
    exp_type = "radical" if is_cold_start else "incremental"
    research_output = {
        "research_insight": meta_res.research_insight,
        "hypothesis": meta_res.hypothesis,
        "research_reasoning": meta_res.research_reasoning,
        "confidence": 0.85 if is_baseline_beat else 0.50,
        "is_cold_start": is_cold_start,
        "weekly_score": weekly_score,
        "is_baseline_beat": is_baseline_beat,
    }

    client.table("prompt_experiments").insert(
        {
            "variant_tag": new_tag,
            "prompt_name": "STOCK_PICKER_PROMPT",
            "prompt_content": new_full_prompt,
            "track_id": model_name,
            "week_start": today.isoformat(),
            "week_end": week_end.isoformat(),
            "status": "active",
            "experiment_type": exp_type,
            "parent_tag": parent_tag,
            "change_description": f"Autoresearch mutation for {model_name} from weekly score {weekly_score:.4f} (ColdStart={is_cold_start})",
            "research_output": research_output,
        }
    ).execute()

    # Save research insight memory
    if meta_res.research_insight:
        client.table("memories").insert(
            {
                "content": f"[Stock Picker Insight - {model_name}] {meta_res.research_insight}",
                "memory_type": "AUTORESEARCH_INSIGHT",
                "importance_score": 8 if is_baseline_beat else 5,
                "metadata": {
                    "track_id": model_name,
                    "scope": "stock_picker",
                    "variant_tag": new_tag,
                    "is_baseline_beat": is_baseline_beat,
                    "weekly_score": weekly_score,
                },
            }
        ).execute()

    logger.info(f"Successfully deployed active stock picker variant {new_tag} for {model_name}.")


async def run_stock_picker_autoresearch(
    days: int = 7,
    dry_run: bool = False,
    cold_start: bool | None = None,
) -> None:
    """Entry point for Sunday weekly stock picker autoresearch loop across all model tracks."""
    client = get_supabase_client()
    logger.info("=== Starting Weekly Stock Picker Autoresearch Loop ===")
    failures = 0
    for model_name in TARGET_TRACK_MODELS:
        try:
            await _optimize_stock_track(
                client,
                model_name,
                days=days,
                dry_run=dry_run,
                force_cold_start=cold_start,
            )
        except Exception as e:
            failures += 1
            logger.error(f"Error optimizing stock picker track {model_name}: {e}", exc_info=e)
    if TARGET_TRACK_MODELS and failures == len(TARGET_TRACK_MODELS):
        logger.error("AUTORESEARCH_RESULT: FAILED_ALL_TRACKS | scope=stock_picker")
        raise RuntimeError(f"Stock picker autoresearch failed for all {failures} tracks")
    logger.info("=== Weekly Stock Picker Autoresearch Loop Completed ===")
