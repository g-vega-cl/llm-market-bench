"""Weekly prompt evolution for the TLT bond predictor.

Scoring reuses the daily-predictor ratchet math (close/intraday accuracy,
magnitude capture, conviction) over evaluated TLT predictions. The frozen
header/footer live in `core/llm/bond_predictor_prompts.py`; only the mutable
strategy block is rewritten.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from core.config import DEEPSEEK_FLASH_MODEL, OPENAI_MODEL
from core.conviction_scoring import select_baseline_candidate
from core.db import get_supabase_client
from core.llm.bond_predictor_prompts import (
    BOND_PREDICTOR_PROMPT,
    BOND_PREDICTOR_PROMPT_NAME,
    split_bond_prompt,
)
from core.llm.clients import close_client, get_deepseek_client
from tasks.daily_autoresearch import calculate_daily_ratchet_metrics

logger = logging.getLogger("engine")

PROMPT_NAME = BOND_PREDICTOR_PROMPT_NAME
TARGET_BOND_MODELS = [OPENAI_MODEL, DEEPSEEK_FLASH_MODEL]
LOOKBACK_DAYS = 7

BOND_AUTORESEARCH_TOOLS = [
    "get_treasury_yield_curve",
    "get_today_economic_releases",
    "get_yield_curve_regime",
    "get_macro_options_sentiment",
    "get_calendar_scenario_analysis",
]


class BondMetaPromptResponse(BaseModel):
    """Structured output returned by the bond meta-researcher LLM."""

    new_strategy: str = Field(..., description="Rewritten mutable strategy section for the TLT predictor.")
    research_insight: str | None = Field(default=None, description="Durable lesson from the week.")
    hypothesis: str | None = Field(default=None, description="Testable hypothesis for the mutation.")
    confidence: int = Field(default=50, ge=0, le=100)


def _slug(model_name: str) -> str:
    return model_name.lower().replace("/", "-").replace("~", "")


def _fetch_week_predictions(client: Any, model_name: str, cutoff: str) -> list[dict]:
    """Return evaluated TLT predictions for the model since cutoff."""
    res = (
        client.table("daily_predictions")
        .select("*")
        .eq("ticker", "TLT")
        .eq("model_name", model_name)
        .eq("status", "evaluated")
        .gte("target_date", cutoff)
        .execute()
    )
    return res.data or []


def _fetch_all_variants(client: Any, model_name: str) -> list[dict]:
    res = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", PROMPT_NAME)
        .eq("track_id", model_name)
        .execute()
    )
    return res.data or []


def _resolve_active_bond_prompt(client: Any, model_name: str, dry_run: bool = False) -> tuple[str, str]:
    """Return (variant_tag, prompt_content), seeding the baseline when absent."""
    for status in ("active", "baseline"):
        res = (
            client.table("prompt_experiments")
            .select("*")
            .eq("prompt_name", PROMPT_NAME)
            .eq("track_id", model_name)
            .eq("status", status)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["variant_tag"], res.data[0]["prompt_content"]

    tag = f"bond-baseline-{_slug(model_name)}"
    if dry_run:
        return tag, BOND_PREDICTOR_PROMPT

    today = datetime.now(UTC).date()
    client.table("prompt_experiments").upsert(
        {
            "variant_tag": tag,
            "prompt_name": PROMPT_NAME,
            "prompt_content": BOND_PREDICTOR_PROMPT,
            "track_id": model_name,
            "week_start": today.isoformat(),
            "week_end": (today + timedelta(days=LOOKBACK_DAYS)).isoformat(),
            "status": "baseline",
            "experiment_type": "baseline",
            "change_description": f"Initial seeded bond baseline for {model_name}.",
        },
        on_conflict="variant_tag",
    ).execute()
    return tag, BOND_PREDICTOR_PROMPT


def resolve_ratchet(
    all_variants: list[dict],
    parent_tag: str,
    weekly_score: float,
    current_prompt: str,
) -> dict[str, Any]:
    """Compare the week's score with the track baseline and pick the prompt to mutate."""
    best = select_baseline_candidate(all_variants, parent_tag)
    if best is None:
        return {
            "parent_tag": parent_tag,
            "current_prompt": current_prompt,
            "baseline_score": -1.0,
            "is_baseline_beat": True,
        }

    baseline_score = float(best[0])
    baseline_variant = best[1] or {}
    is_beat = weekly_score >= baseline_score
    if is_beat:
        return {
            "parent_tag": parent_tag,
            "current_prompt": current_prompt,
            "baseline_score": baseline_score,
            "is_baseline_beat": True,
        }
    return {
        "parent_tag": baseline_variant.get("variant_tag") or parent_tag,
        "current_prompt": baseline_variant.get("prompt_content") or current_prompt,
        "baseline_score": baseline_score,
        "is_baseline_beat": False,
    }


async def _generate_mutation(
    current_prompt: str,
    metrics: dict,
    model_name: str,
    cold_start: bool,
) -> BondMetaPromptResponse:
    _, mutable, _ = split_bond_prompt(current_prompt)
    system_instruction = (
        "You are an elite fixed-income quantitative researcher optimizing a TLT "
        "open-to-close directional predictor. Rewrite only the mutable strategy "
        "section; the frozen mechanics and output contract are managed by code."
    )
    user_msg = (
        f"Track Model: {model_name}\n"
        f"Prior-week score: {metrics.get('score', 0.0):.2f}/100\n"
        f"Close accuracy: {metrics.get('close_accuracy_pct', 0.0):.1f}%\n"
        f"Intraday hit rate: {metrics.get('intraday_hit_pct', 0.0):.1f}%\n"
        f"Magnitude capture: {metrics.get('magnitude_capture_pct', 0.0):.1f}%\n"
        f"Predictions evaluated: {metrics.get('predictions_evaluated', 0)}\n"
        f"Cold start: {cold_start}\n\n"
        f"Current strategy section:\n{mutable}\n\n"
        "Return a mutated strategy section and a durable research insight."
    )

    client = get_deepseek_client()
    try:
        return await client.chat.completions.create(
            model=DEEPSEEK_FLASH_MODEL,
            response_model=BondMetaPromptResponse,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )
    finally:
        await close_client(client, "deepseek")


async def run_bond_autoresearch(dry_run: bool = False, cold_start: bool | None = None) -> list[dict[str, Any]]:
    """Run the weekly TLT bond prompt ratchet across the tool-loop models."""
    from autoresearch.runner import roll_cold_start_dice

    client = get_supabase_client()
    today = datetime.now(UTC).date()
    cutoff = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    results: list[dict[str, Any]] = []

    for model_name in TARGET_BOND_MODELS:
        predictions = _fetch_week_predictions(client, model_name, cutoff)
        if not predictions:
            logger.info(
                f"BOND AUTORESEARCH ({model_name}): no evaluated TLT predictions in {LOOKBACK_DAYS}d. Skipping."
            )
            results.append({"model": model_name, "status": "skipped"})
            continue

        metrics = calculate_daily_ratchet_metrics(predictions)
        weekly_score = float(metrics["score"])
        previous_tag, current_prompt = _resolve_active_bond_prompt(client, model_name, dry_run=dry_run)
        all_variants = _fetch_all_variants(client, model_name)

        decision = resolve_ratchet(all_variants, previous_tag, weekly_score, current_prompt)
        parent_tag = decision["parent_tag"]
        current_prompt = decision["current_prompt"]

        wants_cold = roll_cold_start_dice() if cold_start is None else cold_start
        is_cold_start = bool(wants_cold and decision["baseline_score"] >= 0)

        if not dry_run and not decision["is_baseline_beat"]:
            client.table("prompt_experiments").update({"status": "discarded"}).eq("variant_tag", previous_tag).execute()

        if dry_run:
            results.append(
                {
                    "model": model_name,
                    "status": "dry_run",
                    "score": weekly_score,
                    "parent_tag": parent_tag,
                    "is_baseline_beat": decision["is_baseline_beat"],
                }
            )
            continue

        mutation = await _generate_mutation(current_prompt, metrics, model_name, is_cold_start)
        header, _, footer = split_bond_prompt(current_prompt)
        strategy = mutation.new_strategy.strip()
        new_prompt = header + strategy + footer
        new_tag = f"bond-pred-{_slug(model_name)}-{uuid.uuid4().hex[:8]}"

        client.table("prompt_experiments").update({"status": "saved"}).eq("prompt_name", PROMPT_NAME).eq(
            "track_id", model_name
        ).eq("status", "active").execute()

        client.table("prompt_experiments").insert(
            {
                "variant_tag": new_tag,
                "prompt_name": PROMPT_NAME,
                "prompt_content": new_prompt,
                "track_id": model_name,
                "week_start": today.isoformat(),
                "week_end": (today + timedelta(days=LOOKBACK_DAYS)).isoformat(),
                "status": "active",
                "experiment_type": "radical" if is_cold_start else "incremental",
                "parent_tag": parent_tag,
                "change_description": (f"Bond autoresearch mutation for {model_name} from score {weekly_score:.2f}"),
                "research_output": {
                    "research_insight": mutation.research_insight,
                    "hypothesis": mutation.hypothesis,
                    "confidence": mutation.confidence,
                    "is_cold_start": is_cold_start,
                    "weekly_score": weekly_score,
                    "is_baseline_beat": decision["is_baseline_beat"],
                    "selected_tools": BOND_AUTORESEARCH_TOOLS,
                },
            }
        ).execute()

        if mutation.research_insight:
            try:
                from memory.store import add_memory

                add_memory(
                    content=f"[{model_name.upper()} BOND PREDICTOR INSIGHT] {mutation.research_insight}",
                    memory_type="AUTORESEARCH_INSIGHT",
                    importance_score=9 if decision["is_baseline_beat"] else 5,
                    metadata={
                        "scope": "bond_predictor",
                        "track_id": model_name,
                        "variant_tag": new_tag,
                        "ratchet_score": weekly_score,
                        "is_baseline_beat": decision["is_baseline_beat"],
                    },
                    check_similarity=True,
                )
            except Exception as exc:  # noqa: BLE001 - memory is best effort
                logger.warning(f"Failed to record bond autoresearch memory for {model_name}: {exc}")

        logger.info(
            f"BOND RATCHET ({model_name}): score {weekly_score:.2f} → deployed {new_tag} "
            f"(beat_baseline={decision['is_baseline_beat']}, cold_start={is_cold_start})"
        )
        results.append(
            {
                "model": model_name,
                "status": "deployed",
                "variant_tag": new_tag,
                "score": weekly_score,
                "is_baseline_beat": decision["is_baseline_beat"],
            }
        )

    return results


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_bond_autoresearch())
