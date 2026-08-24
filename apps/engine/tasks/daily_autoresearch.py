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


def calculate_magnitude_capture(p: dict) -> float:
    """Calculate magnitude capture percentage (0-100%) for a single prediction."""
    is_correct = p.get("is_correct") is True
    intraday_hit = p.get("intraday_hit") is True or (p.get("intraday_hit") is None and is_correct)

    if not is_correct or not intraday_hit:
        return 0.0

    expected_return_pct = p.get("expected_return_pct")
    exp_pct = abs(float(expected_return_pct)) if expected_return_pct is not None else 0.0

    open_p = p.get("open_price") or p.get("actual_open_price")
    high_p = p.get("high_price") or p.get("actual_high_price")
    low_p = p.get("low_price") or p.get("actual_low_price")
    close_p = p.get("close_price") or p.get("actual_close_price")
    predicted_dir = (p.get("predicted_direction") or ("UP" if is_correct else "DOWN")).upper()

    if open_p and open_p > 0:
        close_return = abs((close_p - open_p) / open_p) * 100.0 if close_p else 0.0
        if predicted_dir == "UP":
            peak_return = max(0.0, ((high_p - open_p) / open_p) * 100.0) if high_p else close_return
        else:
            peak_return = max(0.0, ((open_p - low_p) / open_p) * 100.0) if low_p else close_return

        actual_move = max(peak_return, close_return)
        if actual_move > 0:
            return min(1.0, exp_pct / actual_move) * 100.0
        return 100.0 if exp_pct == 0 else 0.0

    return 100.0


def calculate_daily_ratchet_metrics(predictions: list[dict]) -> dict:
    """Calculate the full ratchet performance metrics breakdown for daily predictions.

    Score is based on:
    - EOD Close Directional Accuracy % (weight: 0.55)
    - Intraday Target Hit Rate % (weight: 0.35)
    - Magnitude Capture Ratio % (weight: 0.10)
    - Mean Brier Score penalty (penalty multiplier: 50.0)
    Combined Score = (0.55 * close_acc) + (0.35 * hit_rate) + (0.10 * mag_capture) - (mean_brier * 50.0).
    """
    if not predictions:
        return {
            "score": 0.0,
            "close_accuracy_pct": 0.0,
            "intraday_hit_pct": 0.0,
            "magnitude_capture_pct": 0.0,
            "mean_brier": 0.25,
            "predictions_evaluated": 0,
            "correct_count": 0,
            "intraday_hit_count": 0,
        }

    correct_count = sum(1 for p in predictions if p.get("is_correct") is True)
    close_accuracy_pct = (correct_count / len(predictions)) * 100.0

    intraday_hit_count = sum(
        1
        for p in predictions
        if p.get("intraday_hit") is True or (p.get("intraday_hit") is None and p.get("is_correct") is True)
    )
    intraday_hit_pct = (intraday_hit_count / len(predictions)) * 100.0

    magnitude_captures = [calculate_magnitude_capture(p) for p in predictions]
    mean_mag_capture = sum(magnitude_captures) / len(magnitude_captures)

    brier_scores = [p.get("brier_score") for p in predictions if p.get("brier_score") is not None]
    mean_brier = (sum(brier_scores) / len(brier_scores)) if brier_scores else 0.25

    final_score = (
        (0.55 * close_accuracy_pct) + (0.35 * intraday_hit_pct) + (0.10 * mean_mag_capture) - (mean_brier * 50.0)
    )
    return {
        "score": round(float(final_score), 4),
        "close_accuracy_pct": round(float(close_accuracy_pct), 2),
        "intraday_hit_pct": round(float(intraday_hit_pct), 2),
        "magnitude_capture_pct": round(float(mean_mag_capture), 2),
        "mean_brier": round(float(mean_brier), 4),
        "predictions_evaluated": len(predictions),
        "correct_count": correct_count,
        "intraday_hit_count": intraday_hit_count,
    }


def calculate_daily_ratchet_score(predictions: list[dict]) -> float:
    """Calculate the ratchet performance score for daily predictions."""
    return float(calculate_daily_ratchet_metrics(predictions)["score"])


def compute_magnitude_postmortem_summary(predictions: list[dict]) -> str:
    """Generate a structured markdown postmortem analyzing magnitude calibration and timid vs overshooting errors."""
    if not predictions:
        return "No recent prediction history available."

    lines = [
        "### RECENT PREDICTIONS POSTMORTEM & MAGNITUDE CALIBRATION",
        "| Date | Dir | Pred % | Peak % | Close % | Correct? | Hit? | Brier | Capture % | Diagnosis |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    timid_cases = []
    overshot_cases = []

    for p in predictions:
        date_str = str(p.get("target_date") or p.get("prediction_date") or "N/A")[:10]
        direction = str(p.get("predicted_direction") or "N/A").upper()
        exp_pct = float(p.get("expected_return_pct") or 0.0)
        open_p = p.get("open_price") or p.get("actual_open_price")
        high_p = p.get("high_price") or p.get("actual_high_price")
        low_p = p.get("low_price") or p.get("actual_low_price")
        close_p = p.get("close_price") or p.get("actual_close_price")
        is_correct = p.get("is_correct") is True
        intraday_hit = p.get("intraday_hit") is True or (p.get("intraday_hit") is None and is_correct)
        brier = float(p.get("brier_score") or 0.0)
        capture = calculate_magnitude_capture(p)

        peak_pct = 0.0
        close_pct = 0.0
        if open_p and open_p > 0:
            if close_p:
                close_pct = ((close_p - open_p) / open_p) * 100.0
            if direction == "UP" and high_p:
                peak_pct = ((high_p - open_p) / open_p) * 100.0
            elif direction == "DOWN" and low_p:
                peak_pct = ((low_p - open_p) / open_p) * 100.0
            else:
                peak_pct = close_pct

        diagnosis = "Normal"
        actual_move = max(abs(peak_pct), abs(close_pct))
        if is_correct and intraday_hit:
            if actual_move >= 0.60 and capture < 40.0:
                diagnosis = "Timid / Underestimated"
                timid_cases.append(
                    f"- **{date_str}**: Predicted {direction} {exp_pct:+.2f}%, but market moved {actual_move:+.2f}% (only {capture:.1f}% captured). Strong momentum was left on the table."
                )
            else:
                diagnosis = "Well-Calibrated"
        elif not intraday_hit and is_correct:
            if abs(exp_pct) >= 0.60:
                diagnosis = "Overshot / Missed Target"
                overshot_cases.append(
                    f"- **{date_str}**: Target {exp_pct:+.2f}% was too aggressive for actual intraday range (peak {peak_pct:+.2f}%)."
                )
            else:
                diagnosis = "Missed Target"
        else:
            diagnosis = "Wrong Direction"

        lines.append(
            f"| {date_str} | {direction} | {exp_pct:+.2f}% | {peak_pct:+.2f}% | {close_pct:+.2f}% | "
            f"{'Yes' if is_correct else 'No'} | {'Yes' if intraday_hit else 'No'} | {brier:.3f} | {capture:.1f}% | {diagnosis} |"
        )

    lines.append("\n#### Magnitude Calibration Diagnosis:")
    if timid_cases:
        lines.append(
            "**Timid / Underestimated Instances (Need more aggressive magnitude on high-conviction catalysts):**"
        )
        lines.extend(timid_cases)
    else:
        lines.append("- No severe underestimation instances detected in recent sample.")

    if overshot_cases:
        lines.append("**Overshot / Missed Target Instances (Target was set beyond available volatility):**")
        lines.extend(overshot_cases)
    else:
        lines.append("- No severe overshooting errors detected.")

    return "\n".join(lines)


async def generate_new_daily_prompt(
    old_prompt: str,
    baseline_score: float,
    predictions: list[dict] | None = None,
    meta_researcher=None,
) -> str:
    """Generate a mutated strategy instruction prompt using DeepSeek Flash."""
    _, mutable_strategies, _ = split_daily_predictor_prompt(old_prompt)

    postmortem_context = (
        compute_magnitude_postmortem_summary(predictions)
        if predictions
        else "No recent prediction postmortem available."
    )

    meta_prompt = (
        "You are a Meta-Researcher AI optimizing an LLM prompt for predicting intraday S&P 500 (SPY) open-to-close price movement.\n\n"
        f"The current prompt strategy achieved a ratchet score of {baseline_score:.2f}.\n\n"
        f"{postmortem_context}\n\n"
        "### OBJECTIVES & MUTATION RULES:\n"
        "1. Prioritize Directional Accuracy (55% weight) and Intraday Hit Rate (35% weight) first and foremost.\n"
        "2. Optimize Magnitude Calibration (10% weight): When high-impact catalysts or strong trend conditions align, "
        "instruct the predictor to be more confident and aggressive in expected_return_pct magnitude (e.g. +0.50% to +1.20% instead of timid +0.20%).\n"
        "3. On rangebound, ambiguous, or high-VIX days, keep expected_return_pct conservative (+0.15% to +0.25%) to ensure target hit reliability.\n"
        "4. Rewrite ONLY the strategy / analytical reasoning section of the prompt. "
        "Do NOT include output formatting rules or JSON schema definitions; the output structure is automatically enforced.\n\n"
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

    current_metrics = calculate_daily_ratchet_metrics(predictions)
    current_score = current_metrics["score"]

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
        # Fallback to model track baseline
        prompt_response = (
            client.table("prompt_experiments")
            .select("*")
            .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
            .eq("track_id", model_name)
            .eq("status", "baseline")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

    if not prompt_response.data:
        # If no variants exist yet for this model, seed the baseline
        from tasks.daily_predictor import seed_daily_predictor_prompt

        tag, content = await seed_daily_predictor_prompt(model_name=model_name)
        prompt_response = (
            client.table("prompt_experiments")
            .select("*")
            .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
            .eq("track_id", model_name)
            .eq("variant_tag", tag)
            .execute()
        )

    if not prompt_response.data:
        logger.warning(f"No active DAILY_PREDICTOR_PROMPT found for {model_name}. Cannot run daily autoresearch.")
        return

    current_prompt = prompt_response.data[0]["prompt_content"]
    parent_tag = prompt_response.data[0]["variant_tag"]

    # 3. Update active prompt metrics with full breakdown
    client.table("prompt_experiments").update({"metrics": current_metrics}).eq("variant_tag", parent_tag).execute()

    # 4. Fetch baseline variants to perform ratchet comparison strictly within this model track
    all_variants_resp = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
        .eq("track_id", model_name)
        .execute()
    )
    all_variants = all_variants_resp.data or []

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

    # 5. Mutate prompt using DeepSeek Flash
    new_prompt = await generate_new_daily_prompt(
        old_prompt=current_prompt,
        baseline_score=current_score,
        predictions=predictions,
        meta_researcher=deepseek_meta,
    )

    # 6. Deploy new active prompt variant scoped to track_id, demoting prior active variants
    new_tag = f"daily-pred-{model_name}-{uuid.uuid4().hex[:8]}"
    week_end = today + timedelta(days=7)

    # Demote all existing active variants for this model track to saved
    client.table("prompt_experiments").update({"status": "saved"}).eq("prompt_name", "DAILY_PREDICTOR_PROMPT").eq(
        "track_id", model_name
    ).eq("status", "active").execute()

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
