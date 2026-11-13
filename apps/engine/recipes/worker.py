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

JobOutcome = Literal["EMPTY", "COMPLETED", "FAILED"]
SUPPORTED_JOB_MODES = ("backtest", "live_turn")


async def async_process_next_recipe_job(client: Any | None = None) -> JobOutcome:
    """Pop and asynchronously process the next Push v2 recipe job from the priority queue.

    Returns:
        "EMPTY" when no pending job exists,
        "COMPLETED" when the popped job succeeds,
        "FAILED" when the popped job raises or uses an unsupported payload/mode.
    """
    sb = client or get_supabase_client()
    job: dict[str, Any] = {}

    try:
        rpc_res = sb.rpc("pop_next_recipe_job").execute()
        jobs = rpc_res.data or []
        if not jobs:
            return "EMPTY"

        job = jobs[0]
        job_id = job["job_id"]
        mode = str(job.get("job_mode") or "backtest")
        logger.info("Processing recipe job %s (mode=%s, priority=%s)", job_id, mode, job.get("job_priority"))

        if mode not in SUPPORTED_JOB_MODES:
            raise ValueError(f"Unsupported recipe execution mode: {mode}")

        sb.table("recipe_execution_queue").update(
            {
                "status": "processing",
                "started_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", job_id).execute()

        recipe_id = job["job_recipe_id"]
        res = sb.table("strategy_recipes").select("*").eq("id", recipe_id).single().execute()
        recipe_data = res.data or {}
        graph_dict = recipe_data.get("graph_json", {})
        if isinstance(graph_dict, str):
            graph_dict = json.loads(graph_dict)

        if not (isinstance(graph_dict, dict) and isinstance(graph_dict.get("stages"), list)):
            raise ValueError("Recipe must use Push v2 format with a 'stages' list (legacy DAG format is removed).")

        # PushStrategy enforces exactly one LLM stage; a second stage fails here
        # and the job is marked failed with the schema message.
        push_strategy = PushStrategy(**graph_dict)

        if mode == "live_turn":
            result = await run_push_live(push_strategy, sb)
            for sig in result.get("signals", []):
                sb.table("recipe_alerts_inbox").insert(
                    {
                        "user_id": job.get("job_user_id", recipe_data.get("user_id")),
                        "recipe_id": recipe_id,
                        "recipe_name": push_strategy.name,
                        "ticker": sig["ticker"],
                        "action": sig["action"],
                        "entry_price": 0.0,
                        "timeframe": push_strategy.cadence,
                        "reason": result.get("final_output", "")[:500],
                        "context": {"stages": len(result.get("stages", []))},
                        "is_read": False,
                    }
                ).execute()
        else:
            result = await run_push_backtest(push_strategy, sb)

        sb.table("recipe_execution_queue").update(
            {
                "status": "completed",
                "progress_pct": 100,
                "result_json": result,
                "completed_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", job_id).execute()

        current_trials = int(recipe_data.get("trial_count", 0))
        sb.table("strategy_recipes").update(
            {
                "trial_count": current_trials + 1,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", recipe_id).execute()

        return "COMPLETED"

    except Exception as exc:
        logger.exception("Error processing recipe queue job")
        if job.get("job_id"):
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
        return "FAILED"


def process_next_recipe_job(client: Any | None = None) -> JobOutcome:
    """Synchronous wrapper around async_process_next_recipe_job for non-async callers."""
    return asyncio.run(async_process_next_recipe_job(client))
