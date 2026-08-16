import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel

from core.config import logger
from core.db import get_supabase_client
from core.llm.clients import close_client, get_gemini_client
from core.llm.predictor_prompts import (
    SECTOR_PREDICTOR_CONSTRAINTS_FOOTER,
    SECTOR_PREDICTOR_CONSTRAINTS_HEADER,
    split_predictor_prompt,
)


class MetaPromptResponse(BaseModel):
    new_prompt: str


def calculate_baseline_score(predictions: list[dict]) -> float:
    """Calculate the baseline ratchet score from a set of model predictions.

    Formula:
    For each prediction:
      - Percentiles: best sector percentile score, worst sector percentile score (if available), pair percentile score.
      - Base Score = Average of available percentile scores.
      - S&P Alpha Bonus = max(0.0, sector_sp_diff) if sector_sp_diff is available,
        else max(0.0, predicted_sector_return - benchmark_spy_return) if both exist, else 0.0.
      - Prediction Score = Base Score + S&P Alpha Bonus.
    Ratchet Baseline Score = Avg(Prediction Scores) - (Mean Brier Score * 50.0).
    """
    if not predictions:
        return 0.0

    pred_scores = []
    brier_scores = []

    for p in predictions:
        s_score = p.get("sector_percentile_score")
        w_score = p.get("worst_sector_percentile_score")
        p_score = p.get("pair_percentile_score")

        components = [s for s in (s_score, w_score, p_score) if s is not None]
        if not components:
            continue

        base_score = sum(components) / len(components)

        # Calculate S&P alpha bonus for the picked sector
        sp_diff = p.get("sector_sp_diff")
        if sp_diff is None:
            sec_ret = p.get("predicted_sector_return")
            spy_ret = p.get("benchmark_spy_return")
            if sec_ret is not None and spy_ret is not None:
                sp_diff = sec_ret - spy_ret

        alpha_bonus = max(0.0, float(sp_diff)) if sp_diff is not None else 0.0
        pred_scores.append(base_score + alpha_bonus)

        brier = p.get("brier_score")
        if brier is not None:
            brier_scores.append(float(brier))

    if not pred_scores:
        return 0.0

    avg_pred_score = sum(pred_scores) / len(pred_scores)
    mean_brier = (sum(brier_scores) / len(brier_scores)) if brier_scores else 0.0
    final_score = avg_pred_score - (mean_brier * 50.0)
    return float(final_score)


async def generate_new_prompt(old_prompt: str, baseline_score: float, meta_researcher) -> str:
    """Generate a new prompt variant."""
    _, mutable_strategies, _ = split_predictor_prompt(old_prompt)

    meta_prompt = (
        "You are a Meta-Researcher AI tasked with improving an LLM's system prompt "
        "for predicting the best performing market sectors and uncorrelated pairs.\n\n"
        f"The current prompt strategy achieved a percentile score of {baseline_score:.1f}/100.0.\n"
        "Your goal is to rewrite ONLY the strategy / analytical reasoning section of the prompt "
        "to be more effective, focusing on deeper logic, macro quantitative signals, and better data extraction. "
        "Do NOT include any output formatting instructions or JSON schemas in your output; "
        "the required output format is enforced automatically by the system.\n\n"
        "CURRENT STRATEGY INSTRUCTIONS:\n"
        f"```text\n{mutable_strategies}\n```\n\n"
        "Output ONLY the new raw strategy instructions text."
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
        return SECTOR_PREDICTOR_CONSTRAINTS_HEADER + new_strategies + SECTOR_PREDICTOR_CONSTRAINTS_FOOTER
    except Exception as e:
        logger.error(f"Error generating new prompt: {e}")
        return old_prompt


async def run_predictor_autoresearch():
    client = get_supabase_client()

    today = datetime.now(UTC).date()
    seven_days_ago = today - timedelta(days=7)

    # 1. Fetch evaluated predictions from the last week
    response = (
        client.table("sector_predictions")
        .select("*")
        .eq("status", "evaluated")
        .gte("target_date", seven_days_ago.isoformat())
        .lte("target_date", today.isoformat())
        .execute()
    )

    predictions = response.data
    if not predictions:
        logger.info("No evaluated predictions found in the last week. Skipping autoresearch.")
        return

    # Calculate weekly score using baseline ratchet formula (including Brier penalty)
    weekly_score = calculate_baseline_score(predictions)

    # 2. Fetch current active prompt
    prompt_response = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "SECTOR_PREDICTOR_PROMPT")
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not prompt_response.data:
        logger.warning("No active SECTOR_PREDICTOR_PROMPT found. Cannot run autoresearch.")
        return

    current_prompt = prompt_response.data[0]["prompt_content"]
    parent_tag = prompt_response.data[0]["variant_tag"]

    # 3. Update the active prompt variant metrics in DB
    client.table("prompt_experiments").update({"metrics": {"score": weekly_score}}).eq(
        "variant_tag", parent_tag
    ).execute()
    logger.info(f"Updated prompt variant {parent_tag} with weekly score {weekly_score:.4f}")

    # 4. Fetch all-time baseline prompt variant to perform ratchet comparison
    all_variants = client.table("prompt_experiments").select("*").eq("prompt_name", "SECTOR_PREDICTOR_PROMPT").execute()

    baseline_score = -1.0
    baseline_tag = parent_tag
    baseline_content = current_prompt

    for v in all_variants.data:
        if v["variant_tag"] == parent_tag:
            continue
        m = v.get("metrics") or {}
        score = m.get("score")
        if score is not None and score > baseline_score:
            baseline_score = score
            baseline_tag = v["variant_tag"]
            baseline_content = v["prompt_content"]

    # Compare weekly score with baseline
    if baseline_score != -1.0 and weekly_score < baseline_score:
        logger.info(
            f"RATCHET: Weekly score {weekly_score:.4f} failed to beat baseline {baseline_score:.4f}. Reverting to {baseline_tag}."
        )
        # Revert active prompt in DB to baseline content and mark as discarded
        client.table("prompt_experiments").update({"status": "discarded"}).eq("variant_tag", parent_tag).execute()
        current_prompt = baseline_content
        parent_tag = baseline_tag
    else:
        logger.info(
            f"RATCHET: Weekly score {weekly_score:.4f} beats/equals baseline {baseline_score:.4f}. Establishing {parent_tag} as baseline."
        )
        client.table("prompt_experiments").update({"status": "baseline"}).eq("variant_tag", parent_tag).execute()
        # Demote all other active/baseline predictor prompts to saved
        client.table("prompt_experiments").update({"status": "saved"}).in_("status", ["active", "baseline"]).eq(
            "prompt_name", "SECTOR_PREDICTOR_PROMPT"
        ).neq("variant_tag", parent_tag).execute()

    # 5. Generate new prompt mutated from (post-revert) current_prompt
    meta_researcher = get_gemini_client()
    try:
        new_prompt = await generate_new_prompt(current_prompt, weekly_score, meta_researcher)
    finally:
        await close_client(meta_researcher, "gemini")

    # 6. Insert new prompt and set status to active
    new_tag = f"sector-pred-{uuid.uuid4().hex[:8]}"
    week_end = today + timedelta(days=7)

    client.table("prompt_experiments").insert(
        {
            "variant_tag": new_tag,
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "prompt_content": new_prompt,
            "week_start": today.isoformat(),
            "week_end": week_end.isoformat(),
            "status": "active",
            "experiment_type": "incremental",
            "parent_tag": parent_tag,
            "change_description": f"Autoresearch generated from baseline {weekly_score:.1f}",
        }
    ).execute()

    logger.info(f"Successfully generated and deployed new predictor prompt: {new_tag}")


if __name__ == "__main__":
    asyncio.run(run_predictor_autoresearch())
