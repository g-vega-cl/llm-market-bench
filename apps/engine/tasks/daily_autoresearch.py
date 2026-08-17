import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel

from core.config import DEEPSEEK_FLASH_MODEL, MINIMAX_MODEL, logger
from core.db import get_supabase_client
from core.llm.clients import close_client, get_deepseek_client
from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_CONSTRAINTS_FOOTER,
    DAILY_PREDICTOR_CONSTRAINTS_HEADER,
    split_daily_predictor_prompt,
)


class DailyMetaPromptResponse(BaseModel):
    new_prompt: str


def calculate_daily_ratchet_score(predictions: list[dict]) -> float:
    """Calculate the ratchet performance score for daily predictions.

    Score is based on:
    - EOD Close Directional Accuracy % (weight: 0.60)
    - Intraday Target Hit Rate % (weight: 0.40)
    - Mean Brier Score penalty (penalty multiplier: 50.0)
    Combined Score = (0.60 * close_accuracy_pct) + (0.40 * intraday_hit_pct) - (mean_brier * 50.0).
    """
    if not predictions:
        return 0.0

    correct_count = sum(1 for p in predictions if p.get("is_correct") is True)
    close_accuracy_pct = (correct_count / len(predictions)) * 100.0

    intraday_hit_count = sum(
        1
        for p in predictions
        if p.get("intraday_hit") is True or (p.get("intraday_hit") is None and p.get("is_correct") is True)
    )
    intraday_hit_pct = (intraday_hit_count / len(predictions)) * 100.0

    brier_scores = [p.get("brier_score") for p in predictions if p.get("brier_score") is not None]
    mean_brier = (sum(brier_scores) / len(brier_scores)) if brier_scores else 0.25

    final_score = (0.60 * close_accuracy_pct) + (0.40 * intraday_hit_pct) - (mean_brier * 50.0)
    return float(final_score)


async def generate_new_daily_prompt(old_prompt: str, baseline_score: float, meta_researcher) -> str:
    """Generate a mutated strategy instruction prompt using DeepSeek Flash."""
    _, mutable_strategies, _ = split_daily_predictor_prompt(old_prompt)

    meta_prompt = (
        "You are a Meta-Researcher AI optimizing an LLM prompt for predicting intraday S&P 500 (SPY) open-to-close price movement.\n\n"
        f"The current prompt strategy achieved a ratchet score of {baseline_score:.2f}.\n"
        "Your goal is to rewrite ONLY the strategy / analytical reasoning section of the prompt "
        "to be more effective, focusing on macro catalyst extraction, technical level signals, momentum vs gap-fill behavior, "
        "and better confidence calibration.\n"
        "Do NOT include output formatting rules or JSON schema definitions; "
        "the required output structure is automatically enforced by the system.\n\n"
        "CURRENT STRATEGY INSTRUCTIONS:\n"
        f"```text\n{mutable_strategies}\n```\n\n"
        "Output ONLY the raw new strategy instructions text."
    )

    try:
        resp_awaitable = meta_researcher.chat.completions.create(
            model="deepseek-v4-flash",
            response_model=DailyMetaPromptResponse,
            messages=[{"role": "user", "content": meta_prompt}],
        )
        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable

        new_strategies = resp.new_prompt.strip()
        if new_strategies.startswith("```"):
            lines = new_strategies.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            new_strategies = "\n".join(lines).strip()

        return DAILY_PREDICTOR_CONSTRAINTS_HEADER + new_strategies + DAILY_PREDICTOR_CONSTRAINTS_FOOTER
    except Exception as e:
        logger.error(f"Error generating new daily predictor prompt: {e}")
        return old_prompt


async def run_daily_autoresearch_for_model(model_name: str, client, today, four_days_ago, deepseek_meta):
    """Run prompt evolution and ratchet check for a single daily predictor model track."""
    # 1. Fetch evaluated daily predictions for this model over recent 3-4 days
    response = (
        client.table("daily_predictions")
        .select("*")
        .eq("status", "evaluated")
        .eq("model_name", model_name)
        .gte("target_date", four_days_ago.isoformat())
        .lte("target_date", today.isoformat())
        .execute()
    )

    predictions = response.data
    if not predictions:
        logger.info(f"No evaluated daily predictions found for {model_name} in recent days. Skipping autoresearch.")
        return

    current_score = calculate_daily_ratchet_score(predictions)

    # 2. Fetch active prompt variant for this model track
    prompt_response = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
        .eq("track_id", model_name)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not prompt_response.data:
        # Fallback to un-tracked active prompt if not yet track-isolated
        prompt_response = (
            client.table("prompt_experiments")
            .select("*")
            .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

    if not prompt_response.data:
        logger.warning(f"No active DAILY_PREDICTOR_PROMPT found for {model_name}. Cannot run daily autoresearch.")
        return

    current_prompt = prompt_response.data[0]["prompt_content"]
    parent_tag = prompt_response.data[0]["variant_tag"]

    # 3. Update active prompt metrics
    client.table("prompt_experiments").update(
        {"metrics": {"score": current_score, "predictions_evaluated": len(predictions)}}
    ).eq("variant_tag", parent_tag).execute()

    # 4. Fetch baseline variants to perform ratchet comparison
    all_variants_resp = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
        .eq("track_id", model_name)
        .execute()
    )
    all_variants = all_variants_resp.data
    if not all_variants:
        all_variants = (
            client.table("prompt_experiments").select("*").eq("prompt_name", "DAILY_PREDICTOR_PROMPT").execute().data
        )

    baseline_score = -100.0
    baseline_tag = parent_tag
    baseline_content = current_prompt

    for v in all_variants:
        if v["variant_tag"] == parent_tag:
            continue
        m = v.get("metrics") or {}
        score = m.get("score")
        if score is not None and score > baseline_score:
            baseline_score = score
            baseline_tag = v["variant_tag"]
            baseline_content = v["prompt_content"]

    # Compare recent score with baseline
    if baseline_score != -100.0 and current_score < baseline_score:
        logger.info(
            f"DAILY RATCHET ({model_name}): Score {current_score:.2f} failed to beat baseline {baseline_score:.2f}. "
            f"Reverting to baseline {baseline_tag}."
        )
        client.table("prompt_experiments").update({"status": "discarded"}).eq("variant_tag", parent_tag).execute()
        current_prompt = baseline_content
        parent_tag = baseline_tag
    else:
        logger.info(
            f"DAILY RATCHET ({model_name}): Score {current_score:.2f} beats/equals baseline {baseline_score:.2f}. "
            f"Establishing {parent_tag} as new baseline."
        )
        client.table("prompt_experiments").update({"status": "baseline"}).eq("variant_tag", parent_tag).execute()
        client.table("prompt_experiments").update({"status": "saved"}).in_("status", ["active", "baseline"]).eq(
            "prompt_name", "DAILY_PREDICTOR_PROMPT"
        ).eq("track_id", model_name).neq("variant_tag", parent_tag).execute()

    # 5. Mutate prompt using DeepSeek Flash
    new_prompt = await generate_new_daily_prompt(current_prompt, current_score, deepseek_meta)

    # 6. Deploy new active prompt variant scoped to track_id
    new_tag = f"daily-pred-{model_name}-{uuid.uuid4().hex[:8]}"
    week_end = today + timedelta(days=7)

    client.table("prompt_experiments").insert(
        {
            "variant_tag": new_tag,
            "prompt_name": "DAILY_PREDICTOR_PROMPT",
            "prompt_content": new_prompt,
            "track_id": model_name,
            "week_start": today.isoformat(),
            "week_end": week_end.isoformat(),
            "status": "active",
            "experiment_type": "incremental",
            "parent_tag": parent_tag,
            "change_description": f"Daily autoresearch mutation for {model_name} from score {current_score:.2f}",
        }
    ).execute()

    logger.info(f"Successfully mutated and deployed new daily predictor prompt variant for {model_name}: {new_tag}")


async def run_daily_autoresearch():
    """Run twice-weekly prompt evolution and ratchet check independently for both predictor models."""
    client = get_supabase_client()
    today = datetime.now(UTC).date()
    four_days_ago = today - timedelta(days=4)

    target_models = [DEEPSEEK_FLASH_MODEL, MINIMAX_MODEL]
    deepseek_meta = get_deepseek_client()

    try:
        for model_name in target_models:
            await run_daily_autoresearch_for_model(
                model_name=model_name,
                client=client,
                today=today,
                four_days_ago=four_days_ago,
                deepseek_meta=deepseek_meta,
            )
    finally:
        await close_client(deepseek_meta, "deepseek")


if __name__ == "__main__":
    asyncio.run(run_daily_autoresearch())
