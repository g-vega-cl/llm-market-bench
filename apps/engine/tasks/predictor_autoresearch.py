import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel, Field

from core.config import (
    DEEPSEEK_FLASH_MODEL,
    GEMINI_MODEL,
    MINIMAX_MODEL,
    OPENAI_MODEL,
    logger,
)
from core.db import get_supabase_client
from core.llm.clients import close_client, get_gemini_client
from core.llm.predictor_prompts import (
    SECTOR_PREDICTOR_CONSTRAINTS_FOOTER,
    SECTOR_PREDICTOR_CONSTRAINTS_HEADER,
    split_predictor_prompt,
)

TARGET_SECTOR_MODELS = [DEEPSEEK_FLASH_MODEL, MINIMAX_MODEL, GEMINI_MODEL, OPENAI_MODEL]


class MetaPromptResponse(BaseModel):
    new_prompt: str = Field(
        ..., description="The complete modified strategy and analytical reasoning instructions text"
    )
    research_insight: str | None = Field(
        default=None,
        description=(
            "A durable strategic takeaway on sector rotation, macro alpha, or correlation dynamics "
            "to preserve in long-term memory for this model track."
        ),
    )


DEFAULT_SECTOR_PREDICTOR_TOOLS = [
    "get_historical_correlation",
    "get_sector_fundamentals",
    "get_global_macro_context",
    "fetch_daily_newsletter",
    "get_macro_economic_series",
    "run_stock_screener",
    "find_uncorrelated_assets",
    "get_volatility_metrics",
]


def calculate_baseline_metrics(predictions: list[dict]) -> dict:
    """Calculate the weekly baseline ratchet metrics for a model's sector predictions.

    Ratchet Baseline Score = Avg(Prediction Scores) - (Mean Brier Score * 50.0).
    """
    if not predictions:
        return {
            "score": 0.0,
            "base_percentile": 50.0,
            "alpha_bonus": 0.0,
            "mean_brier": 0.25,
            "predictions_evaluated": 0,
        }

    pred_scores = []
    base_percentiles = []
    alpha_bonuses = []
    brier_scores = []

    for p in predictions:
        s_score = p.get("sector_percentile_score")
        w_score = p.get("worst_sector_percentile_score")
        p_score = p.get("pair_percentile_score")

        components = [s for s in (s_score, w_score, p_score) if s is not None]
        if not components:
            continue

        base_score = sum(components) / len(components)
        base_percentiles.append(base_score)

        # Calculate S&P alpha bonus for the picked sector
        sp_diff = p.get("sector_sp_diff")
        if sp_diff is None:
            sec_ret = p.get("predicted_sector_return")
            spy_ret = p.get("benchmark_spy_return")
            if sec_ret is not None and spy_ret is not None:
                sp_diff = sec_ret - spy_ret

        alpha_bonus = max(0.0, float(sp_diff)) if sp_diff is not None else 0.0
        alpha_bonuses.append(alpha_bonus)
        pred_scores.append(base_score + alpha_bonus)

        brier = p.get("brier_score")
        if brier is not None:
            brier_scores.append(float(brier))

    if not pred_scores:
        return {
            "score": 0.0,
            "base_percentile": 50.0,
            "alpha_bonus": 0.0,
            "mean_brier": 0.25,
            "predictions_evaluated": 0,
        }

    avg_base_percentile = sum(base_percentiles) / len(base_percentiles)
    avg_alpha_bonus = sum(alpha_bonuses) / len(alpha_bonuses)
    mean_brier = (sum(brier_scores) / len(brier_scores)) if brier_scores else 0.0
    final_score = (avg_base_percentile + avg_alpha_bonus) - (mean_brier * 50.0)

    return {
        "score": float(final_score),
        "base_percentile": float(avg_base_percentile),
        "alpha_bonus": float(avg_alpha_bonus),
        "mean_brier": float(mean_brier),
        "predictions_evaluated": len(pred_scores),
    }


def calculate_baseline_score(predictions: list[dict]) -> float:
    return calculate_baseline_metrics(predictions)["score"]


async def generate_new_prompt(
    old_prompt: str,
    baseline_score: float,
    meta_researcher,
    track_memories: str = "",
    model_name: str | None = None,
    cold_start: bool = False,
) -> tuple[str, str | None]:
    """Generate a new prompt variant."""
    _, mutable_strategies, _ = split_predictor_prompt(old_prompt)

    mem_block = ""
    if track_memories:
        track_label = model_name or "CURRENT TRACK"
        mem_block = f"\n### PRIOR AUTORESEARCH INSIGHTS & LESSONS (Track: {track_label}):\n{track_memories}\n"

    if cold_start:
        strategy_block = (
            "=== COLD START RESET (STRATEGY FROM SCRATCH) ===\n"
            "This cycle is a COLD START RESET (1-in-6 stochastic exploration to avoid local optima).\n"
            "DO NOT anchor on or adapt the prior strategy. Generate entirely novel, high-conviction analytical reasoning and rotation rules from scratch.\n"
            "Remember that system header rules and the required JSON output schema are FROZEN and automatically appended.\n"
            "Output ONLY the new raw strategy instructions text."
        )
    else:
        strategy_block = (
            "CURRENT STRATEGY INSTRUCTIONS:\n"
            f"```text\n{mutable_strategies}\n```\n\n"
            "Output ONLY the new raw strategy instructions text."
        )

    meta_prompt = (
        "You are a Meta-Researcher AI tasked with improving an LLM's system prompt "
        "for predicting the best performing market sectors and uncorrelated pairs.\n\n"
        f"The current prompt strategy achieved a percentile score of {baseline_score:.1f}/100.0.\n"
        f"{mem_block}\n"
        "Your goal is to rewrite ONLY the strategy / analytical reasoning section of the prompt "
        "to be more effective, focusing on deeper logic, macro quantitative signals, and better data extraction. "
        "Do NOT include any output formatting instructions or JSON schemas in your output; "
        "the required output format is enforced automatically by the system.\n\n"
        "Provide a concise `research_insight` (1-2 sentences) summarizing the key sector rotation or correlation "
        "principle discovered from this evaluation cycle to persist in this track's institutional memory.\n\n"
        f"{strategy_block}"
    )

    try:
        resp_awaitable = meta_researcher.chat.completions.create(
            model="gemini-3.5-flash-lite",
            response_model=MetaPromptResponse,
            messages=[{"role": "user", "content": meta_prompt}],
        )
        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable
        new_strategies = resp.new_prompt
        # Clean up any markdown blocks if the LLM wrapped the output
        if new_strategies.startswith("```"):
            lines = new_strategies.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            new_strategies = "\n".join(lines).strip()

        _, clean_strategies, _ = split_predictor_prompt(new_strategies)
        assembled_prompt = SECTOR_PREDICTOR_CONSTRAINTS_HEADER + clean_strategies + SECTOR_PREDICTOR_CONSTRAINTS_FOOTER
        insight = getattr(resp, "research_insight", None)
        if insight:
            insight = insight.strip()
        return assembled_prompt, insight
    except Exception as e:
        logger.error(f"Error generating new prompt: {e}")
        return old_prompt, None


async def run_predictor_autoresearch_for_model(
    model_name: str,
    client,
    today,
    seven_days_ago,
    meta_researcher,
    dry_run: bool = False,
    cold_start: bool | None = None,
):
    """Run weekly prompt evolution, track isolation, and ratchet check for a single sector predictor model."""
    from autoresearch.runner import roll_cold_start_dice

    is_cold_start = roll_cold_start_dice() if cold_start is None else cold_start
    if is_cold_start:
        logger.info(
            f"COLD START: Stochastic 1-in-6 dice triggered fresh sector rotation strategy from 0 for {model_name}"
        )

    # 1. Fetch evaluated predictions from the last week for this specific model
    response = (
        client.table("sector_predictions")
        .select("*")
        .eq("status", "evaluated")
        .eq("model_name", model_name)
        .gte("target_date", seven_days_ago.isoformat())
        .lte("target_date", today.isoformat())
        .execute()
    )

    predictions = response.data
    if not predictions:
        logger.info(f"No evaluated sector predictions found for {model_name} in the last week. Skipping autoresearch.")
        return

    # Calculate weekly score using baseline ratchet formula (including Brier penalty)
    weekly_metrics = calculate_baseline_metrics(predictions)
    weekly_score = weekly_metrics["score"]

    # 2. Fetch current active prompt for this model track
    prompt_response = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "SECTOR_PREDICTOR_PROMPT")
        .eq("track_id", model_name)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not prompt_response.data:
        # Check model track baseline
        prompt_response = (
            client.table("prompt_experiments")
            .select("*")
            .eq("prompt_name", "SECTOR_PREDICTOR_PROMPT")
            .eq("track_id", model_name)
            .eq("status", "baseline")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

    if not prompt_response.data:
        # Seed baseline for this model track
        from tasks.sector_predictor import fetch_active_prompt

        tag, content = await fetch_active_prompt(model_name=model_name)
        prompt_response = (
            client.table("prompt_experiments")
            .select("*")
            .eq("prompt_name", "SECTOR_PREDICTOR_PROMPT")
            .eq("track_id", model_name)
            .eq("variant_tag", tag)
            .execute()
        )

    if not prompt_response.data:
        logger.warning(f"No active prompt found for {model_name} and seeding failed. Skipping autoresearch.")
        return

    parent_tag = prompt_response.data[0]["variant_tag"]
    current_prompt = prompt_response.data[0]["prompt_content"]

    if dry_run:
        logger.info(f"[DRY RUN] Would update metrics for {parent_tag}: {weekly_metrics}")
    else:
        client.table("prompt_experiments").update({"metrics": weekly_metrics}).eq("variant_tag", parent_tag).execute()
    logger.info(f"Updated prompt variant {parent_tag} ({model_name}) with weekly score {weekly_score:.4f}")

    # 4. Fetch all variants for ratchet check strictly within this model track
    all_variants = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "SECTOR_PREDICTOR_PROMPT")
        .eq("track_id", model_name)
        .execute()
    )

    baseline_score = -1.0
    baseline_tag = parent_tag
    baseline_content = current_prompt

    for v in all_variants.data or []:
        if v["variant_tag"] == parent_tag:
            continue
        m = v.get("metrics") or {}
        score = m.get("score")
        if score is not None and score > baseline_score:
            baseline_score = score
            baseline_tag = v["variant_tag"]
            baseline_content = v["prompt_content"]

    is_baseline_beat = (baseline_score == -1.0) or (weekly_score >= baseline_score)

    # Compare weekly score with baseline
    if baseline_score != -1.0 and weekly_score < baseline_score:
        logger.info(
            f"SECTOR RATCHET ({model_name}): Weekly score {weekly_score:.4f} failed to beat baseline {baseline_score:.4f}. "
            f"Reverting to {baseline_tag}."
        )
        if not dry_run:
            client.table("prompt_experiments").update({"status": "discarded"}).eq("variant_tag", parent_tag).execute()
        current_prompt = baseline_content
        parent_tag = baseline_tag
    else:
        logger.info(
            f"SECTOR RATCHET ({model_name}): Weekly score {weekly_score:.4f} beats/equals baseline {baseline_score:.4f}. "
            f"Establishing {parent_tag} as baseline."
        )
        if not dry_run:
            client.table("prompt_experiments").update({"status": "baseline"}).eq("variant_tag", parent_tag).execute()
            client.table("prompt_experiments").update({"status": "saved"}).in_("status", ["active", "baseline"]).eq(
                "prompt_name", "SECTOR_PREDICTOR_PROMPT"
            ).eq("track_id", model_name).neq("variant_tag", parent_tag).execute()

    # 5. Fetch isolated memories for this sector track
    track_memories = ""
    try:
        from memory.store import retrieve_autoresearch_memories

        track_memories = retrieve_autoresearch_memories(track_id=model_name, scope="sector_predictor", limit=5)
    except Exception as e:
        logger.warning(f"Error fetching autoresearch memories for {model_name}: {e}")

    # 6. Generate new prompt mutated from (post-revert) current_prompt
    new_prompt, research_insight = await generate_new_prompt(
        current_prompt,
        weekly_score,
        meta_researcher,
        track_memories=track_memories,
        model_name=model_name,
        cold_start=is_cold_start,
    )

    # 7. Insert new prompt and set status to active
    new_tag = f"sector-pred-{model_name}-{uuid.uuid4().hex[:8]}"
    week_end = today + timedelta(days=7)

    if research_insight:
        if dry_run:
            logger.info(f"[DRY RUN] Would record sector memory for {model_name}: {research_insight}")
        else:
            try:
                from memory.store import add_memory

                importance = 9 if is_baseline_beat else 6
                add_memory(
                    content=f"[{model_name.upper()} SECTOR PREDICTOR INSIGHT] {research_insight}",
                    memory_type="AUTORESEARCH_INSIGHT",
                    importance_score=importance,
                    metadata={
                        "scope": "sector_predictor",
                        "track_id": model_name,
                        "model_name": model_name,
                        "ratchet_score": weekly_score,
                        "baseline_score": baseline_score if baseline_score != -1.0 else None,
                        "is_baseline_beat": is_baseline_beat,
                        "variant_tag": new_tag,
                    },
                    check_similarity=True,
                )
                logger.info(f"Recorded autoresearch memory for {model_name}: {research_insight[:80]}...")
            except Exception as e:
                logger.warning(f"Failed to record autoresearch memory for {model_name}: {e}")

    if dry_run:
        logger.info(
            f"[DRY RUN] Would deploy new sector prompt variant for {model_name}: {new_tag}\n"
            f"[DRY RUN] Parent Tag: {parent_tag}\n"
            f"[DRY RUN] Mutated Content Preview:\n{new_prompt[:300]}..."
        )
        return

    # Demote all existing active variants for this model track to saved
    client.table("prompt_experiments").update({"status": "saved"}).eq("prompt_name", "SECTOR_PREDICTOR_PROMPT").eq(
        "track_id", model_name
    ).eq("status", "active").execute()

    research_output = {
        "research_insight": research_insight,
        "hypothesis": research_insight,
        "thought_process": research_insight,
        "research_reasoning": research_insight,
        "confidence": 0.85 if is_baseline_beat else 0.50,
        "selected_tools": DEFAULT_SECTOR_PREDICTOR_TOOLS,
        "is_cold_start": is_cold_start,
    }

    exp_type = "radical" if is_cold_start else "incremental"
    desc = (
        f"Weekly sector autoresearch cold start (from 0) for {model_name}"
        if is_cold_start
        else f"Autoresearch generated for {model_name} from score {weekly_score:.1f}"
    )

    client.table("prompt_experiments").insert(
        {
            "variant_tag": new_tag,
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "prompt_content": new_prompt,
            "track_id": model_name,
            "week_start": today.isoformat(),
            "week_end": week_end.isoformat(),
            "status": "active",
            "experiment_type": exp_type,
            "parent_tag": parent_tag,
            "change_description": desc,
            "research_output": research_output,
        }
    ).execute()

    logger.info(f"Successfully generated and deployed new predictor prompt for {model_name}: {new_tag}")


async def run_predictor_autoresearch(
    dry_run: bool = False,
    target_models: list[str] | None = None,
    cold_start: bool | None = None,
):
    """Run weekly prompt evolution across all 4 sector predictor model tracks."""
    client = get_supabase_client()

    today = datetime.now(UTC).date()
    seven_days_ago = today - timedelta(days=7)

    if target_models is None:
        target_models = TARGET_SECTOR_MODELS

    meta_researcher = get_gemini_client()
    from autoresearch.runner import roll_cold_start_dice

    cold_start_triggered = False
    try:
        for model_name in target_models:
            if cold_start is True:
                m_cold = True
            elif cold_start is False:
                m_cold = False
            else:
                # Automated mode: roll 1-in-6 dice with max-1 guardrail
                if not cold_start_triggered and roll_cold_start_dice():
                    m_cold = True
                    cold_start_triggered = True
                else:
                    m_cold = False

            await run_predictor_autoresearch_for_model(
                model_name=model_name,
                client=client,
                today=today,
                seven_days_ago=seven_days_ago,
                meta_researcher=meta_researcher,
                dry_run=dry_run,
                cold_start=m_cold,
            )
    finally:
        await close_client(meta_researcher, "gemini")


if __name__ == "__main__":
    asyncio.run(run_predictor_autoresearch())
