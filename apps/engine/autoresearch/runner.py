"""Auto-research runner — top-level orchestrator.

Runs the weekly auto-research cycle:
1. Safety check (did the prompt crash trading?)
2. Evaluate past week's performance (single score + baseline Δ)
3. Call auto-research LLM to propose prompt changes
4. Always deploy the new variant — no gate, every week iterates
5. Save and activate

Analogous to Karpathy's experiment loop in autoresearch.
"""

import logging
import random
from datetime import date

from core.config import AUTORESEARCH_EXPERIMENT_OWNER_IDS
from core.db import get_async_supabase_client

from .evaluator import evaluate_week
from .prompt_store import (
    get_active_variant,
    get_baseline_metrics,
    revert_to_baseline,
    revert_to_previous,
    save_variant,
    update_variant_metrics,
)
from .researcher import run_research
from .window import get_week_window

logger = logging.getLogger("engine")

SAFETY_MIN_TRADES = 2


def get_next_cold_start_interval(min_weeks: int = 2, max_weeks: int = 5) -> int:
    """Return a stochastic (randomized) interval in weeks for the next cold start reset."""
    return random.randint(min_weeks, max_weeks)


def should_trigger_cold_start(current_cycle: int, target_cycle: int) -> bool:
    """Check whether the current evaluation cycle matches or exceeds the target cold start cycle."""
    return current_cycle >= target_cycle


async def _check_safety(
    week_start: date, week_end: date, owner_list: list[str] | None = None, track_id: str | None = None
) -> tuple[bool, str]:
    """Check if the current active prompt caused a crash.

    A "crash" is: fewer than SAFETY_MIN_TRADES executed trades across all
    experiment agents over the evaluation week. We query the trades table
    (not decisions) because a decision marked EXECUTED may fail at settlement.

    Returns (is_crash, reason).
    """
    sb_client = await get_async_supabase_client()
    if owner_list is None:
        if track_id:
            from core.config import AUTORESEARCH_TRACKS

            owner_list = list(AUTORESEARCH_TRACKS.get(track_id, AUTORESEARCH_EXPERIMENT_OWNER_IDS))
        else:
            owner_list = list(AUTORESEARCH_EXPERIMENT_OWNER_IDS)

    trade_res = await (
        sb_client.table("trades")
        .select("id, portfolios!inner(owner_id)")
        .in_("portfolios.owner_id", owner_list)
        .gte("executed_at", week_start.isoformat())
        .lte("executed_at", f"{week_end.isoformat()}T23:59:59")
        .execute()
    )
    trades = trade_res.data or []
    executed_count = len(trades)

    if executed_count < SAFETY_MIN_TRADES:
        return True, f"Only {executed_count} executed trades (minimum is {SAFETY_MIN_TRADES})"

    return False, ""


async def run(dry_run: bool = False, track_id: str = "track_default", cold_start: bool = False):
    """Run the full auto-research cycle.

    Args:
        dry_run: If True, evaluate and research — but do not write to the
                 database or change the active prompt.
        track_id: ID of the track to optimize prompts for.
        cold_start: If True, generate fresh prompt ignoring past prompt context.
    """
    week_start, week_end = get_week_window()

    label = " DRY RUN" if dry_run else ""
    logger.info("=== Auto-Research Cycle%s (Track: %s) ===", label, track_id)
    if dry_run:
        logger.info("DRY RUN: No database writes will be performed.")
    logger.info("Evaluating week %s to %s", week_start, week_end)

    # Check if the current prompt caused a crash
    try:
        is_crash, crash_reason = await _check_safety(week_start, week_end, track_id=track_id)
    except TypeError:
        is_crash, crash_reason = await _check_safety(week_start, week_end)

    if is_crash:
        logger.warning("SAFETY: %s.", crash_reason)
        if dry_run:
            logger.info("DRY RUN: Would revert to previous prompt.")
        else:
            logger.warning("AUTORESEARCH_RESULT: REVERTED_CRASH | reason=%s", crash_reason)
            try:
                reverted = await revert_to_previous(track_id=track_id)
            except TypeError:
                reverted = await revert_to_previous()
            if reverted:
                logger.info("Reverted to %s. Continuing auto-research generation off baseline.", reverted)
            else:
                logger.warning("No previous variant to revert to. Keeping current prompt.")

    # Evaluate the week
    logger.info("Gathering performance data...")
    try:
        try:
            eval_res = await evaluate_week(week_start, week_end, track_id=track_id)
        except TypeError:
            eval_res = await evaluate_week(week_start, week_end)

        if isinstance(eval_res, tuple) and len(eval_res) == 3:
            report, metrics, baseline_tag = eval_res
        else:
            report, metrics = eval_res[0], eval_res[1]
            baseline_tag = None
    except Exception as e:
        logger.error("Failed to evaluate week: %s", e)
        logger.error("AUTORESEARCH_RESULT: FAILED_EVALUATION | error=%s", e)
        return

    # Fetch currently active variant (the one that ran during the evaluated week, or restored baseline if crashed)
    try:
        active_variant = await get_active_variant(track_id=track_id)
    except TypeError:
        active_variant = await get_active_variant()

    # Log baseline comparison — enforce the Karpathy ratchet.
    # Get baseline metrics BEFORE we update the active variant's metrics in the DB,
    # so we don't accidentally overwrite the baseline we are comparing against.
    score = metrics.get("score", metrics.get("composite", 0.0))
    try:
        baseline_metrics = await get_baseline_metrics(track_id=track_id)
    except TypeError:
        baseline_metrics = await get_baseline_metrics()

    if not dry_run and active_variant and not is_crash:
        await update_variant_metrics(active_variant["variant_tag"], metrics)
        logger.info("Updated active variant %s with evaluated week's metrics", active_variant["variant_tag"])

    parent_tag = baseline_tag
    if is_crash:
        parent_tag = active_variant["variant_tag"] if active_variant else baseline_tag
    elif baseline_metrics:
        baseline_score = baseline_metrics.get("score", 0)
        if score > baseline_score:
            logger.info("RATCHET: New score %.4f BEATS baseline %.4f. New baseline established.", score, baseline_score)
            # If it beats the baseline, this active variant is our new baseline,
            # so the parent tag for the next iteration is this variant's tag!
            parent_tag = active_variant["variant_tag"] if active_variant else baseline_tag
        else:
            logger.info(
                "RATCHET: New score %.4f failed to beat baseline %.4f. Reverting to baseline.", score, baseline_score
            )
            if not dry_run:
                try:
                    reverted = await revert_to_baseline(track_id=track_id)
                except TypeError:
                    reverted = await revert_to_baseline()
                if reverted:
                    logger.info("Active prompt reverted to baseline: %s", reverted)
                    parent_tag = reverted
            else:
                logger.info("DRY RUN: Would revert active prompt to baseline.")
    else:
        logger.info("RATCHET: No baseline found. Establishing first baseline with score %.4f", score)
        parent_tag = active_variant["variant_tag"] if active_variant else baseline_tag

    # Extract baseline mutable text to ensure run_research does not return duplicate text
    from core.llm.prompts import split_prompt

    baseline_prompt_mutable = None
    try:
        from .prompt_store import get_all_time_baseline

        try:
            b_var = await get_all_time_baseline(track_id=track_id)
        except TypeError:
            b_var = await get_all_time_baseline()
        if b_var and b_var.get("prompt_content"):
            _, baseline_prompt_mutable, _ = split_prompt(b_var["prompt_content"])
    except Exception as e:
        logger.warning("Could not resolve baseline mutable prompt: %s", e)

    current_prompt_mutable = None
    if active_variant and active_variant.get("prompt_content"):
        _, current_prompt_mutable, _ = split_prompt(active_variant["prompt_content"])

    # Run the auto-research LLM
    logger.info("Calling auto-research LLM...")
    try:
        try:
            result = await run_research(
                report,
                current_prompt=current_prompt_mutable,
                cold_start=cold_start,
                baseline_prompt=baseline_prompt_mutable,
            )
        except TypeError:
            try:
                result = await run_research(report, cold_start=cold_start)
            except TypeError:
                result = await run_research(report)
    except Exception as e:
        logger.error("Auto-research LLM call failed: %s", e)
        return

    if result is None:
        logger.error("Auto-research returned no result. Skipping prompt update.")
        logger.error("AUTORESEARCH_RESULT: FAILED_RESEARCH | reason=empty_response")
        return

    logger.info(
        "Auto-research result: type=%s, confidence=%d, description=%s",
        result.experiment_type,
        result.confidence,
        result.change_description,
    )

    score = metrics.get("score", metrics.get("composite", 0.0))

    if dry_run:
        logger.info("DRY RUN: Score: %.4f", score)
        logger.info("DRY RUN: Change description: %s", result.change_description)
        logger.info("DRY RUN: Full research output: %s", result.model_dump())
        logger.info("=== Auto-Research Dry Run Complete ===")
        return

    # Save and activate the new variant
    from datetime import timedelta

    next_week_start = week_start + timedelta(days=7)
    next_week_end = week_end + timedelta(days=7)

    from core.llm.prompts import SYSTEM_PROMPT_CONSTRAINTS_FOOTER, SYSTEM_PROMPT_CONSTRAINTS_HEADER

    full_prompt_content = SYSTEM_PROMPT_CONSTRAINTS_HEADER + result.new_prompt_text + SYSTEM_PROMPT_CONSTRAINTS_FOOTER

    try:
        try:
            tag = await save_variant(
                prompt_content=full_prompt_content,
                prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
                week_start=next_week_start.isoformat(),
                week_end=next_week_end.isoformat(),
                metrics={},
                change_description=result.change_description,
                experiment_type=result.experiment_type,
                research_output=result.model_dump(),
                parent_tag=parent_tag,
                track_id=track_id,
            )
        except TypeError:
            tag = await save_variant(
                prompt_content=full_prompt_content,
                prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
                week_start=next_week_start.isoformat(),
                week_end=next_week_end.isoformat(),
                metrics={},
                change_description=result.change_description,
                experiment_type=result.experiment_type,
                research_output=result.model_dump(),
                parent_tag=parent_tag,
            )
        logger.info("New active prompt variant: %s", tag)
    except Exception as e:
        logger.error("Failed to save variant: %s", e)
        logger.error("AUTORESEARCH_RESULT: FAILED_SAVE | error=%s", e)
        return

    logger.info("=== Auto-Research Cycle Complete ===")
    logger.info("Next week's prompt: %s (%s)", tag, result.experiment_type)
    logger.info("AUTORESEARCH_RESULT: SUCCESS | variant=%s | type=%s | score=%.4f", tag, result.experiment_type, score)


async def run_all(dry_run: bool = False, cold_start: bool = False):
    """Run the auto-research cycle across all configured tracks sequentially within the same event loop."""
    from core.config import AUTORESEARCH_TRACKS

    track_ids = list(AUTORESEARCH_TRACKS.keys()) if AUTORESEARCH_TRACKS else ["track_default"]
    for t_id in track_ids:
        logger.info("Executing Auto-Research cycle for track: %s", t_id)
        await run(dry_run=dry_run, track_id=t_id, cold_start=cold_start)
