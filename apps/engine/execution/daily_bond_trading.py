"""Systematic Daily Bond Trading Module (Vertical Slice Island).

Executes systematic daily trades on TLT (20+ Year Treasury Bond ETF) based on daily open-to-close predictions:
- Session Close-Exit Strategy: Holds from 9:30 AM open and exits at session close (3:50 PM / MOC).
- Modeled with 0.02% (2 bps) slippage due to high TLT ETF liquidity.
- Owner ID prefix: `sys-daily-tlt-close-{model_name}`.
"""

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from core.config import logger
from core.db import get_supabase_client
from execution.daily_reconciliation import (
    get_daily_session_open_price,
)
from execution.daily_trading import (
    compute_daily_trade_execution,
    get_or_create_system_portfolio,
)

SYS_DAILY_TLT_CLOSE_OWNER_PREFIX = "sys-daily-tlt-close-"
DEFAULT_BOND_CLOSE_SLIPPAGE_BPS = 2.0  # 2 bps = 0.02% for liquid TLT ETF


async def execute_daily_bond_moo_entries(
    target_date: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute pre-market Market-On-Open (MOO) daily bond trades for TLT.

    - Reads predictions for target_date from daily_predictions table for ticker='TLT'.
    - Sizing uses session open price or latest quote.
    - UP predictions: BUY order / long position.
    - DOWN predictions: SHORT order / short position.
    """
    client = get_supabase_client()
    target_date_str = target_date or date.today().isoformat()

    res = client.table("daily_predictions").select("*").eq("target_date", target_date_str).eq("ticker", "TLT").execute()
    predictions = res.data or []
    if not predictions:
        logger.info(f"No daily bond predictions found for TLT on {target_date_str}. Skipping MOO entry.")
        return {"status": "skipped", "reason": "No predictions found", "entries": []}

    session_open = await get_daily_session_open_price("TLT", target_date_str, client=client)
    if not session_open or session_open <= 0:
        from execution.market_data import MarketDataManager

        mdm = MarketDataManager()
        quote = await mdm.get_premarket_quote("TLT")
        session_open = float(quote.get("price", 0.0)) if quote else 0.0

    if not session_open or session_open <= 0:
        logger.warning(f"Could not retrieve TLT price for MOO entry on {target_date_str}.")
        return {"status": "skipped", "reason": "No TLT price", "entries": []}

    entries = []

    for pred in predictions:
        model_name = str(pred.get("model_name", "unknown"))
        direction = str(pred.get("predicted_direction", "UP")).strip().upper()
        owner_id = f"{SYS_DAILY_TLT_CLOSE_OWNER_PREFIX}{model_name}"

        portfolio = await get_or_create_system_portfolio(owner_id)
        current_cash = portfolio.cash_balance

        # Idempotency check: verify if entry trade already exists for today
        existing_res = (
            client.table("trades")
            .select("id")
            .eq("portfolio_id", str(portfolio.id))
            .gte("executed_at", f"{target_date_str}T00:00:00Z")
            .lte("executed_at", f"{target_date_str}T23:59:59Z")
            .execute()
        )
        if existing_res.data:
            logger.info(f"Entry trade already exists for {owner_id} on {target_date_str}. Skipping re-entry.")
            continue

        shares = int(current_cash // session_open) if session_open > 0 else 0
        if shares <= 0:
            logger.info(f"Insufficient cash (${current_cash:.2f}) for {owner_id} to trade TLT @ ${session_open:.2f}.")
            continue

        trade_signal = "BUY" if direction == "UP" else "SHORT"
        trade_id = str(uuid4())
        entry_trade = {
            "id": trade_id,
            "portfolio_id": str(portfolio.id),
            "ticker": "TLT",
            "signal": trade_signal,
            "quantity": shares,
            "price": session_open,
            "total_cost": shares * session_open,
            "executed_at": f"{target_date_str}T13:30:00Z",
        }

        if not dry_run:
            client.table("trades").insert(entry_trade).execute()

        entries.append(
            {
                "owner_id": owner_id,
                "signal": trade_signal,
                "shares": shares,
                "price": session_open,
            }
        )
        logger.info(f"Executed MOO bond trade for {owner_id}: {trade_signal} {shares} TLT @ ${session_open:.2f}")

    return {"status": "success", "entries": entries}


async def execute_system_daily_bond_close_trade(
    prediction: dict,
    intraday_data: dict,
    slippage_bps: float = DEFAULT_BOND_CLOSE_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Execute close-exit systematic daily trade for TLT portfolio."""
    model_name = prediction.get("model_name", "unknown")
    owner_id = f"{SYS_DAILY_TLT_CLOSE_OWNER_PREFIX}{model_name}"
    target_date_str = prediction.get("target_date") or date.today().isoformat()

    portfolio = await get_or_create_system_portfolio(owner_id)
    current_cash = portfolio.cash_balance
    client = get_supabase_client()

    # Idempotency cleanup for target_date session
    existing_trades_res = (
        client.table("trades")
        .select("id, realized_pnl")
        .eq("portfolio_id", str(portfolio.id))
        .gte("executed_at", f"{target_date_str}T00:00:00Z")
        .lte("executed_at", f"{target_date_str}T23:59:59Z")
        .execute()
    )
    existing_trades = existing_trades_res.data or []
    if existing_trades:
        prev_pnl = sum(float(t["realized_pnl"]) for t in existing_trades if t.get("realized_pnl") is not None)
        current_cash = max(0.0, current_cash - prev_pnl)
        for t in existing_trades:
            client.table("trades").delete().eq("id", t["id"]).execute()

    execution = compute_daily_trade_execution(
        prediction=prediction,
        intraday=intraday_data,
        capital=current_cash,
        slippage_bps=slippage_bps,
        exit_on_target=False,
    )

    shares = execution["shares"]
    if shares <= 0:
        return {"status": "skipped", "reason": "Insufficient capital"}

    direction = execution["direction"]
    entry_signal = "BUY" if direction == "UP" else "SHORT"
    exit_signal = "SELL" if direction == "UP" else "COVER"

    # Log entry trade at 9:30 AM ET
    entry_payload = {
        "portfolio_id": str(portfolio.id),
        "ticker": "TLT",
        "signal": entry_signal,
        "quantity": shares,
        "price": execution["entry_price"],
        "total_cost": shares * execution["entry_price"],
        "executed_at": f"{target_date_str}T13:30:00Z",
    }
    if direction == "DOWN":
        entry_payload["realized_pnl"] = execution["realized_pnl"]
        entry_payload["realized_pnl_pct"] = execution["realized_pnl_pct"]
    client.table("trades").insert(entry_payload).execute()

    # Log exit trade at 4:00 PM ET with realized PnL
    exit_payload = {
        "portfolio_id": str(portfolio.id),
        "ticker": "TLT",
        "signal": exit_signal,
        "quantity": shares,
        "price": execution["exit_price"],
        "total_cost": shares * execution["exit_price"],
        "realized_pnl": execution["realized_pnl"],
        "realized_pnl_pct": execution["realized_pnl_pct"],
        "executed_at": f"{target_date_str}T20:00:00Z",
    }
    client.table("trades").insert(exit_payload).execute()

    new_cash = max(0.0, current_cash + execution["realized_pnl"])
    client.table("portfolios").update(
        {
            "cash_balance": new_cash,
            "total_equity": new_cash,
            "realized": new_cash,
            "buying_power": new_cash * 4,
            "excess_liquidity": new_cash,
            "last_updated_at": datetime.now(UTC).isoformat(),
        }
    ).eq("id", str(portfolio.id)).execute()

    client.table("portfolio_performance").upsert(
        {
            "portfolio_id": str(portfolio.id),
            "date": target_date_str,
            "total_equity": new_cash,
            "cash_balance": new_cash,
            "buying_power": new_cash * 4,
            "sma": 0.0,
            "realized": new_cash,
        },
        on_conflict="portfolio_id,date",
    ).execute()

    logger.info(
        f"Daily TLT trade complete for {owner_id} on {target_date_str}: "
        f"Dir: {direction}, PnL: ${execution['realized_pnl']:,.2f}, Equity: ${new_cash:,.2f}"
    )

    return {
        "status": "success",
        "owner_id": owner_id,
        "execution": execution,
        "new_equity": new_cash,
    }


async def execute_daily_bond_close_exits(
    target_date: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute afternoon close exits (MOC) for TLT daily bond portfolios."""
    client = get_supabase_client()
    target_date_str = target_date or date.today().isoformat()

    from execution.market_data import MarketDataManager

    mdm = MarketDataManager()
    hist = await mdm.get_history("TLT", days=2)
    close_price = float(hist[-1]["price"]) if hist else 0.0

    if not close_price or close_price <= 0:
        logger.warning(f"Could not retrieve TLT close price for close exit on {target_date_str}.")
        return {"status": "skipped", "reason": "No close price"}

    preds_res = (
        client.table("daily_predictions").select("*").eq("target_date", target_date_str).eq("ticker", "TLT").execute()
    )
    predictions = preds_res.data or []
    exits = []

    for pred in predictions:
        intraday_data = {
            "open_price": pred.get("open_price") or close_price,
            "high_price": pred.get("high_price") or close_price,
            "low_price": pred.get("low_price") or close_price,
            "close_price": close_price,
        }
        res = await execute_system_daily_bond_close_trade(
            prediction=pred,
            intraday_data=intraday_data,
        )
        exits.append(res)

    return {"status": "success", "exits": exits}
