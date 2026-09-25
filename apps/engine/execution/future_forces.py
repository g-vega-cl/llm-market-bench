"""Future Forces & Forward Catalysts Execution Engine (`sys-future-forces`).

Executes multi-horizon thematic force allocations (2 to 24 months):
1. Retains healthy active forces through intermediate market volatility.
2. Enforces market hours guardrail: Liquidations and buys ONLY execute during
   regular market trading hours (09:30 - 16:00 ET). If market is closed,
   marks force status as 'pending_liquidation' to execute at next market open.
3. Every order executes in real time via Portfolio.execute_trade, mirroring
   to Alpaca paper broker for third-party auditability with zero retroactive backfilling.
"""

from datetime import UTC, datetime
from typing import Any

from core.config import logger
from core.db import get_supabase_client
from core.utils import is_market_open_with_logging
from execution.portfolio import Portfolio

SYS_FUTURE_FORCES_OWNER_ID = "sys-future-forces"
DEFAULT_SLIPPAGE_BPS = 5.0
DEFAULT_TARGET_POSITION_WEIGHT = 0.08  # ~8% per position (10 to 15 holdings)


def compute_future_forces_rebalance_orders(
    current_holdings: list[dict[str, Any]],
    holding_evaluations: dict[str, dict[str, Any]],
    candidate_forces: list[dict[str, Any]],
    available_cash: float,
    total_equity: float,
    target_position_weight: float = DEFAULT_TARGET_POSITION_WEIGHT,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Computes liquidations, retentions, and new buy allocations for sys-future-forces."""
    slip_factor = slippage_bps / 10000.0

    sales: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    freed_cash = 0.0

    current_holding_tickers = {h["ticker"].upper() for h in current_holdings if h.get("ticker")}

    # 1. Evaluate existing holdings
    for holding in current_holdings:
        ticker = holding["ticker"].upper()
        shares = int(holding.get("shares") or 0)
        current_p = float(holding.get("current_price") or 0.0)

        ev = holding_evaluations.get(ticker, {"should_exit": False, "reason": "active_force_hold"})
        if ev.get("should_exit"):
            exit_price = current_p * (1.0 - slip_factor)
            sale_value = shares * exit_price
            freed_cash += sale_value
            sales.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "execution_price": exit_price,
                    "sale_value": sale_value,
                    "reason": ev.get("reason", "thesis_invalidation"),
                }
            )
            logger.info(
                "Future Forces: Liquidating %s (%d shares at $%.2f). Reason: %s",
                ticker,
                shares,
                exit_price,
                ev.get("reason"),
            )
        else:
            retained.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "current_price": current_p,
                    "current_value": shares * current_p,
                }
            )

    deployable_cash = available_cash + freed_cash
    target_position_usd = total_equity * target_position_weight
    new_buys: list[dict[str, Any]] = []

    # 2. Allocate into top candidate forces
    for force in candidate_forces:
        tickers = [t.upper() for t in (force.get("tickers") or [])]
        if not tickers:
            continue

        for ticker in tickers:
            if ticker in current_holding_tickers:
                continue  # already held

            quote = force.get("quotes", {}).get(ticker, {})
            price = float(quote.get("price") or 0.0)
            if price <= 0:
                continue

            entry_price = price * (1.0 + slip_factor)
            if deployable_cash < target_position_usd * 0.5:
                break  # insufficient cash remaining

            allocated_usd = min(deployable_cash, target_position_usd)
            shares = int(allocated_usd // entry_price)
            if shares <= 0:
                continue

            actual_cost = shares * entry_price
            deployable_cash -= actual_cost

            new_buys.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "execution_price": entry_price,
                    "total_cost": actual_cost,
                    "force_title": force.get("force_title"),
                    "archetype": force.get("archetype"),
                }
            )
            current_holding_tickers.add(ticker)

    return {
        "sales": sales,
        "retained": retained,
        "new_buys": new_buys,
        "freed_cash": freed_cash,
        "remaining_cash": deployable_cash,
    }


async def execute_force_invalidation(
    force_id: str,
    reason: str,
    is_realized: bool = False,
    force_market_check: bool = True,
) -> dict[str, Any]:
    """Executes ad-hoc liquidation of a force upon thesis death or realization.

    Guards against out-of-market execution: If market is closed, flags status
    as 'pending_liquidation' to execute at next market open.
    """
    supabase = get_supabase_client()
    now = datetime.now(UTC)

    # 1. Fetch force record
    try:
        res = supabase.table("future_forces").select("*").eq("id", force_id).execute()
        if not res.data:
            logger.warning("Future force %s not found in database", force_id)
            return {"status": "error", "message": f"Force {force_id} not found"}
        force = res.data[0]
    except Exception as e:
        logger.debug("Could not query future_forces for force %s: %s", force_id, e)
        return {"status": "error", "message": f"Force {force_id} not accessible in database"}

    tickers = [t.upper() for t in (force.get("tickers") or [])]

    # 2. Check market open guardrail
    if force_market_check:
        market_open = await is_market_open_with_logging()
        if not market_open:
            logger.info(
                "Market is closed. Deferring liquidation of %s (%s) to next market open.",
                force.get("force_title"),
                tickers,
            )
            supabase.table("future_forces").update(
                {
                    "status": "pending_liquidation",
                    "invalidation_reason": reason,
                    "audited_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            ).eq("id", force_id).execute()
            return {
                "status": "deferred_market_closed",
                "force_title": force.get("force_title"),
                "tickers": tickers,
                "reason": reason,
            }

    # 3. Market is open: Execute live trade via Portfolio (mirrors to Alpaca)
    portfolio = Portfolio(SYS_FUTURE_FORCES_OWNER_ID)
    await portfolio.initialize()

    executed_sales = []
    for ticker in tickers:
        pos = portfolio.get_position(ticker)
        if not pos or (pos.get("quantity") or 0) <= 0:
            continue

        shares = int(pos["quantity"])
        # Fetch current price from quote or position
        current_price = float(pos.get("current_price") or pos.get("average_cost_basis") or 100.0)
        exit_price = current_price * (1.0 - (DEFAULT_SLIPPAGE_BPS / 10000.0))

        trade_reason = f"force_realized: {reason}" if is_realized else f"thesis_invalidation: {reason}"

        trade_record = await portfolio.execute_trade(
            ticker=ticker,
            signal="SELL",
            quantity=shares,
            price=exit_price,
            reason=trade_reason,
            skip_alpaca_mirror=False,  # Enforce Alpaca paper audit
        )
        executed_sales.append(trade_record)
        logger.info(
            "Future Forces: Executed live SELL of %s (%d shares at $%.2f) mirrored to Alpaca.",
            ticker,
            shares,
            exit_price,
        )

    # 4. Update status in database
    target_status = "realized" if is_realized else "invalidated"
    try:
        supabase.table("future_forces").update(
            {
                "status": target_status,
                "invalidation_reason": reason,
                "audited_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ).eq("id", force_id).execute()
    except Exception as e:
        logger.debug("Could not update future_forces row status in database: %s", e)

    return {
        "status": "executed",
        "target_status": target_status,
        "force_title": force.get("force_title"),
        "tickers": tickers,
        "sales": executed_sales,
    }
