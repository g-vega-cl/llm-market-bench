"""Queue worker for Push v2 Strategy Recipes: backtests and live turns."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, Literal

from core.config import logger
from core.db import get_supabase_client
from recipes.push_runner import run_push_backtest, run_push_live
from recipes.push_schema import PushStrategy

JobOutcome = Literal["EMPTY", "COMPLETED", "FAILED", "CANCELLED"]
SUPPORTED_JOB_MODES = ("backtest", "live_turn")


def _default_model_for_mode(mode: str) -> str:
    return "auto-go" if mode == "live_turn" else "strata-auto-go"


def _is_job_cancelled(sb: Any, job_id: str) -> bool:
    """Return True only when the queue row was explicitly marked cancelled."""
    try:
        res = sb.table("recipe_execution_queue").select("status").eq("id", job_id).single().execute()
        data = getattr(res, "data", None)
        return isinstance(data, dict) and data.get("status") == "cancelled"
    except Exception:
        return False


def _insert_live_alerts(
    sb: Any,
    job: dict[str, Any],
    recipe_data: dict[str, Any],
    recipe_id: str,
    push_strategy: Any,
    result: dict[str, Any],
) -> None:
    """Insert inbox alerts strictly for executed paper trades (or legacy mock signals when absent)."""
    signal_prices = result.get("signal_prices") or {}
    alerts_to_emit = result["executed_signals"] if "executed_signals" in result else result.get("signals", [])
    for sig in alerts_to_emit:
        sb.table("recipe_alerts_inbox").insert(
            {
                "user_id": job.get("job_user_id", recipe_data.get("user_id")),
                "recipe_id": recipe_id,
                "recipe_name": push_strategy.name,
                "ticker": sig["ticker"],
                "action": sig["action"],
                "entry_price": float(sig.get("price", signal_prices.get(sig["ticker"], 0.0))),
                "timeframe": push_strategy.cadence,
                "reason": result.get("final_output", "")[:500],
                "context": {"stages": len(result.get("stages", [])), "slot_label": result.get("slot_label")},
                "is_read": False,
            }
        ).execute()


def _update_recipe_cas(
    sb: Any,
    recipe_id: str,
    recipe_data: dict[str, Any],
    mode: str,
    result: dict[str, Any],
) -> None:
    """Update trial_count and paper portfolio state guarded by optimistic trial_count CAS."""
    current_trials = int(recipe_data.get("trial_count", 0))
    recipe_update: dict[str, Any] = {
        "trial_count": current_trials + 1,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if mode == "live_turn" and isinstance(result.get("updated_portfolio"), dict):
        recipe_update.update(result["updated_portfolio"])

    cas_res = (
        sb.table("strategy_recipes")
        .update(recipe_update)
        .eq("id", recipe_id)
        .eq("trial_count", current_trials)
        .execute()
    )
    if isinstance(getattr(cas_res, "data", None), list) and len(cas_res.data) == 0:
        logger.warning("Optimistic CAS miss updating recipe %s (expected trial_count=%d)", recipe_id, current_trials)


def _load_validated_recipe(sb: Any, recipe_id: str) -> tuple[dict[str, Any], PushStrategy]:
    """Fetch strategy_recipes row and validate its Push v2 single-stage schema."""
    res = sb.table("strategy_recipes").select("*").eq("id", recipe_id).single().execute()
    recipe_data = res.data or {}
    graph_dict = recipe_data.get("graph_json", {})
    if isinstance(graph_dict, str):
        graph_dict = json.loads(graph_dict)

    if not (isinstance(graph_dict, dict) and isinstance(graph_dict.get("stages"), list)):
        raise ValueError("Recipe must use Push v2 format with a 'stages' list (legacy DAG format is removed).")

    # PushStrategy enforces exactly one LLM stage; a second stage fails here
    # and the job is marked failed with the schema message.
    return recipe_data, PushStrategy(**graph_dict)


async def _execute_recipe_job_mode(
    sb: Any,
    job: dict[str, Any],
    recipe_data: dict[str, Any],
    recipe_id: str,
    job_id: str,
    mode: str,
    push_strategy: PushStrategy,
) -> dict[str, Any]:
    """Run either live_turn or backtest execution for a validated Push v2 recipe."""
    job_model = str(job.get("job_model") or _default_model_for_mode(mode))
    if mode == "live_turn":
        result = await run_push_live(push_strategy, sb, recipe_row=recipe_data, model=job_model)
        _insert_live_alerts(sb, job, recipe_data, recipe_id, push_strategy, result)
        return result

    def _on_progress(progress_pct: int, partial_result: dict[str, Any]) -> None:
        try:
            sb.table("recipe_execution_queue").update(
                {
                    "progress_pct": progress_pct,
                    "result_json": partial_result,
                    "heartbeat_at": datetime.now(UTC).isoformat(),
                }
            ).eq("id", job_id).eq("status", "processing").execute()
        except Exception:
            logger.warning("Failed updating progress for recipe job %s", job_id, exc_info=True)

    return await run_push_backtest(
        push_strategy,
        sb,
        on_progress=_on_progress,
        concurrency_config=recipe_data.get("concurrency_config"),
        model=job_model,
        is_cancelled=lambda: _is_job_cancelled(sb, job_id),
    )


def _record_job_failure(sb: Any, job: dict[str, Any], exc: Exception) -> None:
    """Persist FAILED status on the popped queue row without masking the original error."""
    if not job.get("job_id"):
        return
    try:
        sb.table("recipe_execution_queue").update(
            {
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", job["job_id"]).execute()
    except Exception:
        logger.exception("Failed to record error state on queue job")


async def async_process_next_recipe_job(
    client: Any | None = None,
    *,
    target_mode: str | None = None,
) -> JobOutcome:
    """Pop and asynchronously process the next Push v2 recipe job from the priority queue.

    Returns:
        "EMPTY" when no pending job exists,
        "COMPLETED" when the popped job succeeds,
        "CANCELLED" when cancelled mid-flight,
        "FAILED" when the popped job raises or uses an unsupported payload/mode.
    """
    sb = client or get_supabase_client()
    job: dict[str, Any] = {}

    try:
        rpc_res = (
            sb.rpc("pop_next_recipe_job", {"target_mode": target_mode}).execute()
            if target_mode is not None
            else sb.rpc("pop_next_recipe_job").execute()
        )
        jobs = rpc_res.data or []
        if not jobs:
            return "EMPTY"

        job = jobs[0]
        job_id = job["job_id"]
        mode = str(job.get("job_mode") or "backtest")
        logger.info(
            "Processing recipe job %s (mode=%s, model=%s, priority=%s)",
            job_id,
            mode,
            job.get("job_model"),
            job.get("job_priority"),
        )

        if mode not in SUPPORTED_JOB_MODES:
            raise ValueError(f"Unsupported recipe execution mode: {mode}")

        now_iso = datetime.now(UTC).isoformat()
        sb.table("recipe_execution_queue").update(
            {
                "status": "processing",
                "started_at": now_iso,
                "heartbeat_at": now_iso,
            }
        ).eq("id", job_id).eq("status", "processing").execute()

        recipe_id = job["job_recipe_id"]
        recipe_data, push_strategy = _load_validated_recipe(sb, recipe_id)
        result = await _execute_recipe_job_mode(sb, job, recipe_data, recipe_id, job_id, mode, push_strategy)

        if _is_job_cancelled(sb, job_id) or (isinstance(result, dict) and result.get("cancelled")):
            logger.info("Recipe job %s was cancelled mid-run; skipping completion update", job_id)
            return "CANCELLED"

        comp_res = (
            sb.table("recipe_execution_queue")
            .update(
                {
                    "status": "completed",
                    "progress_pct": 100,
                    "result_json": result,
                    "completed_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", job_id)
            .eq("status", "processing")
            .execute()
        )
        comp_rows = getattr(comp_res, "data", None)
        if isinstance(comp_rows, list) and len(comp_rows) == 0:
            logger.info("Recipe job %s transitioned externally before completion; skipping CAS", job_id)
            return "CANCELLED"

        _update_recipe_cas(sb, recipe_id, recipe_data, mode, result)
        return "COMPLETED"

    except Exception as exc:
        logger.exception("Error processing recipe queue job")
        _record_job_failure(sb, job, exc)
        return "FAILED"


def process_next_recipe_job(
    client: Any | None = None,
    *,
    target_mode: str | None = None,
) -> JobOutcome:
    """Synchronous wrapper around async_process_next_recipe_job for non-async callers."""
    return asyncio.run(async_process_next_recipe_job(client, target_mode=target_mode))
