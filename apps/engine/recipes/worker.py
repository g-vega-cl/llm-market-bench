"""Queue worker for Strategy Recipes: backtests, previews, and live turns."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from core.config import logger
from core.db import get_supabase_client
from recipes.backtester import run_recipe_backtest
from recipes.indicators import Bar, evaluate_technical_gate
from recipes.schema import ConditionRule, RecipeGraph
from recipes.validator import validate_recipe_graph


def _parse_job_recipe(job_record: dict[str, Any], client: Any) -> tuple[dict[str, Any], RecipeGraph]:
    """Fetch and parse strategy recipe associated with the queue job."""
    recipe_id = job_record["job_recipe_id"]
    res = client.table("strategy_recipes").select("*").eq("id", recipe_id).single().execute()
    recipe_data = res.data or {}
    graph_dict = recipe_data.get("graph_json", {})
    if isinstance(graph_dict, str):
        graph_dict = json.loads(graph_dict)
    recipe_graph = RecipeGraph(**graph_dict)
    return recipe_data, recipe_graph


def _execute_backtest_job(
    job_record: dict[str, Any],
    recipe_graph: RecipeGraph,
    client: Any,
) -> dict[str, Any]:
    """Execute multi-week backtest for the queued job."""
    weeks_req = job_record.get("job_weeks_requested", [])
    if isinstance(weeks_req, str):
        weeks_req = json.loads(weeks_req)
    if not weeks_req:
        weeks_req = ["2026-W10"]

    # Prefetch bars from recipe_intraday_bars
    bars_by_week: dict[str, list[Bar]] = {}
    ticker = "SPY"
    for node in recipe_graph.nodes:
        if node.type == "price_tape" and node.config.get("ticker"):
            ticker = str(node.config["ticker"]).upper().strip()
            break
        if node.type == "news_source" and node.config.get("tickers"):
            raw_t = node.config["tickers"]
            if isinstance(raw_t, list) and raw_t:
                ticker = str(raw_t[0]).upper().strip()
                break
    if ticker == "SPY" and recipe_graph.name:
        candidate = recipe_graph.name.split()[0].upper().strip()
        if candidate.isalpha() and len(candidate) <= 5:
            ticker = candidate

    res_bars = (
        client.table("recipe_intraday_bars")
        .select("*")
        .eq("ticker", ticker)
        .order("bar_time_utc", desc=False)
        .execute()
    )
    raw_bars = res_bars.data or []
    loaded_bars: list[Bar] = []
    for b in raw_bars:
        t = b["bar_time_utc"]
        if isinstance(t, str):
            t = datetime.fromisoformat(t.replace("Z", "+00:00"))
        loaded_bars.append(
            Bar(
                time_utc=t,
                open=float(b["open"]),
                high=float(b["high"]),
                low=float(b["low"]),
                close=float(b["close"]),
                volume=int(b["volume"]),
            )
        )

    # If no bars in DB cache, provide minimal synthetic candle anchor for fallback
    if not loaded_bars:
        now = datetime.now(UTC)
        loaded_bars = [
            Bar(
                time_utc=now,
                open=500.0,
                high=501.0,
                low=499.0,
                close=500.5,
                volume=10000,
            )
        ]

    for wk in weeks_req:
        bars_by_week[str(wk)] = loaded_bars

    # Prefetch news
    news_res = (
        client.table("recipe_news_corpus")
        .select("article_id, title, date_published, tickers, buckets")
        .order("date_published", desc=True)
        .limit(100)
        .execute()
    )
    news_articles = news_res.data or []

    result = run_recipe_backtest(
        recipe=recipe_graph,
        bars_by_week=bars_by_week,
        news_articles=news_articles,
    )
    return result


def _execute_live_turn(
    job_record: dict[str, Any],
    recipe_data: dict[str, Any],
    recipe_graph: RecipeGraph,
    client: Any,
) -> dict[str, Any]:
    """Execute a live turn for an active recipe and deposit alert if triggered."""
    user_id = job_record["job_user_id"]
    recipe_id = job_record["job_recipe_id"]
    recipe_name = recipe_data.get("name", "Strategy Recipe")
    ticker = recipe_name.split()[0] if recipe_name else "SPY"

    # Fetch latest bar
    bar_res = (
        client.table("recipe_intraday_bars")
        .select("*")
        .eq("ticker", ticker)
        .order("bar_time_utc", desc=True)
        .limit(1)
        .execute()
    )
    latest_bar_data = (bar_res.data or [{}])[0]
    now = datetime.now(UTC)
    raw_bar_time = latest_bar_data.get("bar_time_utc")
    if isinstance(raw_bar_time, str):
        bar_time = datetime.fromisoformat(raw_bar_time.replace("Z", "+00:00"))
    elif isinstance(raw_bar_time, datetime):
        bar_time = raw_bar_time
    else:
        bar_time = now

    def _safe_float(val: Any, default: float) -> float:
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    def _safe_int(val: Any, default: int) -> int:
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    current_bar = Bar(
        time_utc=bar_time,
        open=_safe_float(latest_bar_data.get("open"), 500.0),
        high=_safe_float(latest_bar_data.get("high"), 501.0),
        low=_safe_float(latest_bar_data.get("low"), 499.0),
        close=_safe_float(latest_bar_data.get("close"), 500.5),
        volume=_safe_int(latest_bar_data.get("volume"), 5000),
    )

    # Evaluate conditions
    tech_conds = []
    risk_action = "BUY"
    stop_loss_pct = 0.015
    target_profit_pct = 0.03
    for n in recipe_graph.nodes:
        if n.type == "technical_gate":
            for c in n.config.get("conditions", []):
                tech_conds.append(ConditionRule(**c) if isinstance(c, dict) else c)
        elif n.type == "risk_output":
            risk_action = str(n.config.get("action", "BUY")).upper()
            stop_loss_pct = float(n.config.get("stop_loss_pct", 1.5)) / 100.0
            target_profit_pct = float(n.config.get("target_profit_pct", 3.0)) / 100.0

    passed, reasons = evaluate_technical_gate(tech_conds, current_bar)

    if passed:
        if risk_action == "BUY":
            target_price = round(current_bar.close * (1.0 + target_profit_pct), 4)
            stop_loss = round(current_bar.close * (1.0 - stop_loss_pct), 4)
        else:  # SELL / SHORT
            target_price = round(current_bar.close * (1.0 - target_profit_pct), 4)
            stop_loss = round(current_bar.close * (1.0 + stop_loss_pct), 4)

        # Deposit alert into in-app inbox
        alert_payload = {
            "user_id": user_id,
            "recipe_id": recipe_id,
            "recipe_name": recipe_name,
            "ticker": ticker,
            "action": risk_action,
            "entry_price": current_bar.close,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "timeframe": recipe_graph.cadence,
            "reason": f"Live signal triggered: {'; '.join(reasons)}",
            "context": {"bar_time": current_bar.time_utc.isoformat()},
            "is_read": False,
        }
        client.table("recipe_alerts_inbox").insert(alert_payload).execute()
        return {"action_taken": risk_action, "alert_created": True, "price": current_bar.close}

    return {"action_taken": "NONE", "alert_created": False, "reasons": reasons}


def process_next_recipe_job(client: Any | None = None) -> bool:
    """Pop and process the next recipe job from the priority queue.

    Returns True if a job was processed, False if queue was empty.
    """
    sb = client or get_supabase_client()

    try:
        rpc_res = sb.rpc("pop_next_recipe_job").execute()
        jobs = rpc_res.data or []
        if not jobs:
            return False

        job = jobs[0]
        job_id = job["job_id"]
        logger.info(f"Processing recipe job {job_id} (mode={job.get('job_mode')}, priority={job.get('job_priority')})")

        # Mark job as processing
        sb.table("recipe_execution_queue").update(
            {
                "status": "processing",
                "started_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", job_id).execute()

        recipe_data, recipe_graph = _parse_job_recipe(job, sb)
        is_valid, validation_errors = validate_recipe_graph(recipe_graph)
        if not is_valid:
            raise ValueError(f"Recipe validation failed: {'; '.join(validation_errors)}")

        mode = job.get("job_mode", "backtest")

        if mode == "live_turn":
            result = _execute_live_turn(job, recipe_data, recipe_graph, sb)
        else:
            result = _execute_backtest_job(job, recipe_graph, sb)

        # Mark job completed
        sb.table("recipe_execution_queue").update(
            {
                "status": "completed",
                "progress_pct": 100,
                "result_json": result,
                "completed_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", job_id).execute()

        # Increment recipe trial count
        recipe_id = job["job_recipe_id"]
        current_trials = int(recipe_data.get("trial_count", 0))
        sb.table("strategy_recipes").update(
            {
                "trial_count": current_trials + 1,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", recipe_id).execute()

        return True

    except Exception as exc:
        logger.exception("Error processing recipe queue job")
        if "job" in locals() and job.get("job_id"):
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
        return False
