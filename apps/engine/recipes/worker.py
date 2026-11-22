"""Queue worker for Push v2 Strategy Recipes: backtests, live turns, and /build compiles."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import httpx

from core.config import FREE_LLM_PROXY_URL, FREE_PROXY_MASTER_KEY, logger
from core.db import get_supabase_client
from recipes.push_runner import run_push_backtest, run_push_live
from recipes.push_schema import PushStrategy

JobOutcome = Literal["EMPTY", "COMPLETED", "FAILED", "CANCELLED"]
SUPPORTED_JOB_MODES = ("backtest", "live_turn", "compile")

# /build compiles ride the same queue. The daemon is not behind the edge's ~30s
# function ceiling, so it can give the free provider a longer window than the old
# synchronous request did; the web tier keeps the template fallback for failures.
COMPILE_TIMEOUT_SECONDS = 45
BUILDER_DAILY_LIMIT = 25
DEFAULT_COMPILE_PROXY_URL = "https://llm.clvg.uk/v1"
# A compile nobody ever claimed (daemon down, or a burst the lane never reached)
# must not block the per-user 2-pending cap forever. Matches the existing
# 10-minute recovery rule for stalled `processing` rows.
STALE_COMPILE_SECONDS = 600
STALE_COMPILE_MESSAGE = "The worker never picked this compile up. Try again."


def _parse_iso_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def fail_stale_compile_jobs(sb: Any, *, timeout_seconds: int = STALE_COMPILE_SECONDS) -> int:
    """Fail `pending` compile rows no worker claimed, releasing the per-user cap.

    The pop RPC only recovers `processing` rows whose heartbeat lapsed; a row that
    never moved off `pending` has no heartbeat, so without this it would sit forever
    (and the client's give-up path had nothing to cancel).
    """
    now = datetime.now(UTC)
    cutoff = (now - timedelta(seconds=timeout_seconds)).isoformat()
    res = (
        sb.table("recipe_execution_queue")
        .update(
            {
                "status": "failed",
                "error_message": STALE_COMPILE_MESSAGE,
                "completed_at": now.isoformat(),
            }
        )
        .eq("mode", "compile")
        .eq("status", "pending")
        .lt("created_at", cutoff)
        .select("id")
        .execute()
    )
    rows = getattr(res, "data", None)
    return len(rows) if isinstance(rows, list) else 0


def _default_model_for_mode(mode: str) -> str:
    """Both lanes run on the free-llm proxy (auto-go); local Strata is retired for recipes."""
    return "auto-go"


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


async def _execute_compile_job(sb: Any, job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Run one /build compile: meter, POST the stored auto-go request, return the raw reply.

    The prompt and the recipe contract are built and validated by the web tier, so
    this worker stays a generic completion executor — one implementation of the
    model contract, no Python copy of the capability manifest to drift.
    """
    res = (
        sb.table("recipe_execution_queue")
        .select("payload_json, user_id, created_at")
        .eq("id", job_id)
        .single()
        .execute()
    )
    row = getattr(res, "data", None) or {}
    payload = row.get("payload_json")
    if not isinstance(payload, dict) or not payload.get("messages"):
        raise ValueError("compile job has no payload_json messages")

    # The sweep marks unclaimed rows failed, but the pop poll runs every 5s and the
    # sweep only once a minute, so a row that aged past the window could be claimed
    # first. Refuse it here, before the meter and before any tokens are spent.
    created_at = _parse_iso_utc(row.get("created_at"))
    if created_at is not None and (datetime.now(UTC) - created_at).total_seconds() > STALE_COMPILE_SECONDS:
        raise RuntimeError(STALE_COMPILE_MESSAGE)

    user_id = row.get("user_id") or job.get("job_user_id")
    used = sb.rpc("consume_builder_compile", {"p_user": user_id}).execute().data
    if isinstance(used, int) and used > BUILDER_DAILY_LIMIT:
        raise RuntimeError(
            f"Daily builder limit reached ({BUILDER_DAILY_LIMIT} compiles). "
            "Edit an existing recipe or come back tomorrow."
        )

    headers = {"Content-Type": "application/json"}
    key = (FREE_PROXY_MASTER_KEY or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    base_url = (FREE_LLM_PROXY_URL or DEFAULT_COMPILE_PROXY_URL).rstrip("/")

    async with httpx.AsyncClient(timeout=COMPILE_TIMEOUT_SECONDS) as client:
        response = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()

    choices = body.get("choices") or []
    content = (choices[0].get("message") or {}).get("content") if choices else None
    if not content:
        raise RuntimeError("Builder model returned an empty reply")
    return {"content": content}


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

        recipe_data: dict[str, Any] = {}
        recipe_id = job.get("job_recipe_id")
        if mode == "compile":
            result = await _execute_compile_job(sb, job, job_id)
        else:
            if not isinstance(recipe_id, str):
                raise ValueError("recipe job is missing its recipe_id")
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

        if recipe_id:
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
