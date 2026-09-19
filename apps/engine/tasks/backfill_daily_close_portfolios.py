"""Backfill daily close-exit (3:50 PM) systematic portfolios.

Replays evaluated daily predictions from 2026-08-21 through current date for
sys-daily-spy-close-{model} portfolios with 0.02% (2 bps) slippage.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from core.config import logger
from core.db import get_supabase_client
from execution.daily_trading import (
    DEFAULT_DAILY_CLOSE_SLIPPAGE_BPS,
    INITIAL_PORTFOLIO_CASH,
    SYS_DAILY_SPY_CLOSE_OWNER_PREFIX,
    execute_system_daily_close_trade,
    get_or_create_system_portfolio,
)

START_DATE = "2026-08-21"


async def backfill_daily_close_portfolios(
    start_date: str = START_DATE,
    slippage_bps: float = DEFAULT_DAILY_CLOSE_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Replay historical evaluated daily predictions into close-exit portfolios."""
    client = get_supabase_client()

    # Query all evaluated SPY predictions on or after start_date
    res = (
        client.table("daily_predictions")
        .select("*")
        .eq("ticker", "SPY")
        .eq("status", "evaluated")
        .gte("target_date", start_date)
        .order("target_date", desc=False)
        .execute()
    )
    predictions = res.data or []
    if not predictions:
        logger.info(f"No evaluated predictions found on or after {start_date}")
        return {"status": "skipped", "reason": "No predictions"}

    # Group by model
    models = sorted(list({p["model_name"] for p in predictions if p.get("model_name")}))
    results = {}

    for model in models:
        owner_id = f"{SYS_DAILY_SPY_CLOSE_OWNER_PREFIX}{model}"
        portfolio = await get_or_create_system_portfolio(owner_id)

        # Clean existing trades and performance for a clean backfill replay
        client.table("trades").delete().eq("portfolio_id", str(portfolio.id)).execute()
        client.table("portfolio_performance").delete().eq("portfolio_id", str(portfolio.id)).execute()

        # Reset portfolio cash & equity to initial
        client.table("portfolios").update(
            {
                "cash_balance": INITIAL_PORTFOLIO_CASH,
                "total_equity": INITIAL_PORTFOLIO_CASH,
                "realized": INITIAL_PORTFOLIO_CASH,
                "buying_power": INITIAL_PORTFOLIO_CASH * 4,
                "excess_liquidity": INITIAL_PORTFOLIO_CASH,
                "last_updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", str(portfolio.id)).execute()

        model_preds = [p for p in predictions if p.get("model_name") == model]
        trade_count = 0

        for pred in model_preds:
            open_p = pred.get("open_price")
            close_p = pred.get("close_price")
            high_p = pred.get("high_price") or max(open_p, close_p)
            low_p = pred.get("low_price") or min(open_p, close_p)

            if open_p is None or close_p is None:
                continue

            intraday_data = {
                "open_price": open_p,
                "high_price": high_p,
                "low_price": low_p,
                "close_price": close_p,
                "intraday_hit": pred.get("intraday_hit", False),
            }

            trade_res = await execute_system_daily_close_trade(
                prediction=pred,
                intraday_data=intraday_data,
                slippage_bps=slippage_bps,
            )
            if trade_res.get("status") == "success":
                trade_count += 1

        # Fetch final portfolio state
        final_port_res = client.table("portfolios").select("*").eq("id", str(portfolio.id)).single().execute()
        final_equity = final_port_res.data.get("total_equity") if final_port_res.data else None

        results[owner_id] = {
            "sessions_evaluated": trade_count,
            "final_equity": final_equity,
        }
        logger.info(f"Backfill complete for {owner_id}: {trade_count} sessions, Final Equity: ${final_equity:,.2f}")

    return {"status": "success", "results": results}


if __name__ == "__main__":
    asyncio.run(backfill_daily_close_portfolios())
