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
from core.db import get_supabase_client

from .evaluator import evaluate_week
from .researcher import run_research
from .prompt_store import save_variant, revert_to_previous
from .validator import validate_prompt
from .window import get_week_window

logger = logging.getLogger("engine")

SAFETY_MAX_REJECTION_RATE = 0.90
SAFETY_MIN_TRADES = 2


def _check_safety(week_start: date, week_end: date) -> tuple[bool, str]:
    """Check if the current active prompt caused a crash.

    A "crash" is: > SAFETY_MAX_REJECTION_RATE rejection rate OR fewer than
    SAFETY_MIN_TRADES executed trades across all experiment agents over
    the evaluation week.

    Returns (is_crash, reason).
    """
    sb_client = get_supabase_client()
    owner_list = list(AUTORESEARCH_EXPERIMENT_OWNER_IDS)

    decision_res = (
        sb_client.table("decisions")
        .select("status")
        .in_("model_name", owner_list)
        .gte("created_at", week_start.isoformat())
        .lte("created_at", f"{week_end.isoformat()}T23:59:59")
        .execute()
    )
    decisions = decision_res.data or []

    if decisions:
        rejected = sum(1 for d in decisions if (d.get("status") or "").startswith("REJECTED"))
        rejection_rate = rejected / len(decisions)
        executed = sum(1 for d in decisions if d.get("status") == "EXECUTED")
        if rejection_rate > SAFETY_MAX_REJECTION_RATE:
            return True, f"Rejection rate {rejection_rate:.1%} exceeds safety threshold ({SAFETY_MAX_REJECTION_RATE:.1%})"
        if executed < SAFETY_MIN_TRADES:
            return True, f"Only {executed} executed trades (minimum is {SAFETY_MIN_TRADES})"

    return False, ""


async def run():
    """Run the full auto-research cycle.

    This is the entry point called by the CLI (main.py autoresearch).
    """
    week_start, week_end = get_week_window()

    logger.info("=== Auto-Research Cycle ===")
    logger.info("Evaluating week %s to %s", week_start, week_end)

    # Check if the current prompt caused a crash
    is_crash, crash_reason = _check_safety(week_start, week_end)
    if is_crash:
        logger.warning("SAFETY: %s. Reverting to previous prompt.", crash_reason)
        reverted = await revert_to_previous()
        if reverted:
            logger.info("Reverted to %s. Skipping auto-research this week.", reverted)
        else:
            logger.warning("No previous variant to revert to. Keeping current prompt.")
        return

    # Evaluate the week
    logger.info("Gathering performance data...")
    try:
        report, composite = await evaluate_week()
    except Exception as e:
        logger.error("Failed to evaluate week: %s", e)
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
        return

    logger.info(
        "Auto-research result: type=%s, confidence=%d, description=%s",
        result.experiment_type, result.confidence, result.change_description,
    )

    # Reject unsafe prompts before we ever activate them.
    is_valid, reason = validate_prompt(result.new_prompt_text)
    if not is_valid:
        logger.error("Researcher proposal failed safety validation: %s. Skipping activation.", reason)
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
        return

    logger.info("=== Auto-Research Cycle Complete ===")
    logger.info("Next week's prompt: %s (%s)", tag, result.experiment_type)
