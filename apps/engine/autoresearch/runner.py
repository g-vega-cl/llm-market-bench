"""Auto-research runner — top-level orchestrator.

Runs the weekly auto-research cycle:
1. Evaluate past week's performance
2. Call auto-research LLM to propose prompt changes
3. Validate the proposed prompt against safety invariants
4. Check safety conditions on the live agent
5. Save and activate the validated variant

Analogous to Karpathy's experiment loop in autoresearch.
"""

import logging
from datetime import date

from core.config import AUTORESEARCH_EXPERIMENT_OWNER_IDS
from core.db import get_async_supabase_client

from .evaluator import evaluate_week
from .researcher import run_research
from .prompt_store import save_variant, revert_to_previous
from .validator import validate_prompt
from .window import get_week_window

logger = logging.getLogger("engine")

SAFETY_MIN_TRADES = 2


async def _check_safety(week_start: date, week_end: date) -> tuple[bool, str]:
    """Check if the current active prompt caused a crash.

    A "crash" is: fewer than SAFETY_MIN_TRADES executed trades across all
    experiment agents over the evaluation week. We query the trades table
    (not decisions) because a decision marked EXECUTED may fail at settlement.

    Returns (is_crash, reason).
    """
    sb_client = await get_async_supabase_client()
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


async def run(dry_run: bool = False):
    """Run the full auto-research cycle.

    Args:
        dry_run: If True, evaluate, research, and validate — but do not
                 write to the database or change the active prompt.

    This is the entry point called by the CLI (main.py autoresearch).
    """
    week_start, week_end = get_week_window()

    label = " DRY RUN" if dry_run else ""
    logger.info("=== Auto-Research Cycle%s ===", label)
    if dry_run:
        logger.info("DRY RUN: No database writes will be performed.")
    logger.info("Evaluating week %s to %s", week_start, week_end)

    # Check if the current prompt caused a crash
    is_crash, crash_reason = await _check_safety(week_start, week_end)
    if is_crash:
        logger.warning("SAFETY: %s.", crash_reason)
        if dry_run:
            logger.info("DRY RUN: Would revert to previous prompt (skipping).")
        else:
            logger.warning("AUTORESEARCH_RESULT: SKIPPED_CRASH | reason=%s", crash_reason)
            reverted = await revert_to_previous()
            if reverted:
                logger.info("Reverted to %s. Skipping auto-research this week.", reverted)
            else:
                logger.warning("No previous variant to revert to. Keeping current prompt.")
        return

    # Evaluate the week
    logger.info("Gathering performance data...")
    try:
        report, composite = await evaluate_week(week_start, week_end)
    except Exception as e:
        logger.error("Failed to evaluate week: %s", e)
        logger.error("AUTORESEARCH_RESULT: FAILED_EVALUATION | error=%s", e)
        return

    # Run the auto-research LLM
    logger.info("Calling auto-research LLM...")
    try:
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
        result.experiment_type, result.confidence, result.change_description,
    )

    # Reject unsafe prompts before we ever activate them.
    is_valid, reason, warnings_list = validate_prompt(result.new_prompt_text)
    if warnings_list:
        for w in warnings_list:
            logger.warning("Soft invariant violation: %s", w)

    if not is_valid:
        logger.error("Researcher proposal failed safety validation: %s.", reason)
        if dry_run:
            logger.info("DRY RUN: Would have rejected this proposal.")
        else:
            logger.error("AUTORESEARCH_RESULT: FAILED_VALIDATION | reason=%s", reason)
        return

    if dry_run:
        # Gate: only activate if the experiment composite beats baseline.
        baseline = composite.get("baseline_composite", 0)
        exp_score = composite["composite"]
        if baseline > 0 and exp_score <= baseline:
            logger.warning(
                "DRY RUN: Composite %.4f does not beat baseline %.4f — would NOT activate.",
                exp_score, baseline,
            )
        else:
            logger.info("DRY RUN: Prompt validated — would have been saved and activated.")
        logger.info("DRY RUN: Proposed prompt (%s, confidence=%d):",
                     result.experiment_type, result.confidence)
        logger.info("=" * 72)
        logger.info(result.new_prompt_text)
        logger.info("=" * 72)
        logger.info("DRY RUN: Composite score: %.4f (baseline: %.4f)",
                     exp_score, baseline)
        logger.info("DRY RUN: Change description: %s", result.change_description)
        logger.info("DRY RUN: Full research output: %s", result.model_dump())
        logger.info("=== Auto-Research Dry Run Complete ===")
        return

    # Gate: only activate if experiment composite beats baseline.
    baseline = composite.get("baseline_composite", 0)
    exp_score = composite["composite"]
    if baseline > 0 and exp_score <= baseline:
        logger.warning(
            "Composite %.4f does not beat baseline %.4f — skipping activation.",
            exp_score, baseline,
        )
        logger.warning(
            "AUTORESEARCH_RESULT: SKIPPED_NO_IMPROVEMENT | composite=%.4f | baseline=%.4f",
            exp_score, baseline,
        )
        return

    # Save and activate the new variant
    try:
        tag = await save_variant(
            prompt_content=result.new_prompt_text,
            prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            metrics=composite,
            change_description=result.change_description,
            experiment_type=result.experiment_type,
            research_output=result.model_dump(),
        )
        logger.info("New active prompt variant: %s", tag)
    except Exception as e:
        logger.error("Failed to save variant: %s", e)
        logger.error("AUTORESEARCH_RESULT: FAILED_SAVE | error=%s", e)
        return

    logger.info("=== Auto-Research Cycle Complete ===")
    logger.info("Next week's prompt: %s (%s)", tag, result.experiment_type)
    logger.info("AUTORESEARCH_RESULT: SUCCESS | variant=%s | type=%s | composite=%.4f",
                tag, result.experiment_type, composite["composite"])
