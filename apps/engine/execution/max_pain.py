"""Daily Options Max Pain systematic portfolio execution logic.

Handles:
1. Evaluating holding exits (target strike touch within 0.05%, 3:50 PM MOC session close, 1.0% stop loss).
2. Sizing and capital allocation for 0DTE index convergence candidates admitted by Jev.
3. Generating execution rebalance orders with 0.01% (1 bps) friction.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.config import logger

SYS_MAX_PAIN_OWNER_ID = "sys-max-pain"
DEFAULT_MAX_HOLDINGS = 2  # SPY and QQQ primary daily proxies
DEFAULT_MAX_PAIN_SLIPPAGE_BPS = 1.0  # 1 bps = 0.01% for deep liquid index ETFs
DEFAULT_TARGET_PROXIMITY_PCT = 0.05  # Within 0.05% of strike considered pinned
DEFAULT_ADVERSE_STOP_PCT = 1.0  # 1.0% drop from entry signifies gamma support breakdown


def evaluate_max_pain_holding_exit(
    holding_info: dict[str, Any],
    current_price: float,
    session_high: float | None = None,
    is_market_close_window: bool = False,
    target_proximity_pct: float = DEFAULT_TARGET_PROXIMITY_PCT,
    stop_loss_pct: float = DEFAULT_ADVERSE_STOP_PCT,
) -> tuple[bool, str]:
    """Evaluate whether an existing Daily Max Pain holding should be exited.

    Exit Triggers:
    1. Target Strike Pinning: Spot or session high reaches within target_proximity_pct of Max Pain strike.
    2. Session Close Liquidation: 3:50 PM ET market-on-close window reached (zero overnight hold).
    3. Adverse Stop Loss: Current price drops more than stop_loss_pct below entry price.
    """
    target_strike = float(holding_info.get("target_strike", 0.0))
    entry_price = float(holding_info.get("entry_price", 0.0) or holding_info.get("cost_basis", 0.0))
    high_p = float(session_high) if session_high is not None and session_high > 0 else current_price

    # 1. Target Strike Reached (Pin Achieved)
    if target_strike > 0:
        threshold = target_strike * (1.0 - target_proximity_pct / 100.0)
        if high_p >= threshold or current_price >= threshold:
            return True, f"Target strike ${target_strike:.2f} reached (pin achieved)"

    # 2. Session Close Liquidation (MOC, zero overnight hold)
    if is_market_close_window:
        return True, "Session close liquidation (3:50 PM MOC)"

    # 3. Adverse Stop Loss (Gamma breakdown)
    if entry_price > 0 and current_price > 0:
        drawdown_pct = ((entry_price - current_price) / entry_price) * 100.0
        if drawdown_pct >= stop_loss_pct:
            return True, f"Adverse stop loss triggered (-{drawdown_pct:.2f}% below entry ${entry_price:.2f})"

    return False, "Holding criteria healthy"


def compute_max_pain_rebalance_orders(
    current_holdings: list[dict[str, Any]],
    holding_evaluations: dict[str, dict[str, Any]],
    qualified_candidates: list[dict[str, Any]],
    available_cash: float,
    max_holdings: int = DEFAULT_MAX_HOLDINGS,
    slippage_bps: float = DEFAULT_MAX_PAIN_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Computes exact sales and buy orders for the Daily Max Pain portfolio."""
    slip_factor = slippage_bps / 10000.0
    sales: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    freed_cash = 0.0

    # 1. Process sales for holdings marked for exit
    for h in current_holdings:
        ticker = h["ticker"]
        eval_res = holding_evaluations.get(ticker, {})
        if eval_res.get("should_exit", False):
            shares = int(h.get("shares", 0))
            raw_price = float(h.get("current_price", 0.0) or h.get("cost_basis", 0.0))
            reason_str = str(eval_res.get("reason", "Exit rule satisfied"))
            target_strike = float(h.get("target_strike") or 0.0)
            if "pin achieved" in reason_str.lower() and target_strike > 0:
                raw_price = max(raw_price, target_strike)
            exec_price = raw_price * (1.0 - slip_factor)
            proceeds = shares * exec_price
            freed_cash += proceeds
            sales.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "execution_price": exec_price,
                    "proceeds": proceeds,
                    "reason": reason_str,
                }
            )
        else:
            retained.append(h)

    # 2. Determine open slots and candidate selection
    open_slots = max(0, max_holdings - len(retained))
    retained_tickers = {h["ticker"].upper() for h in retained}

    eligible_candidates = [c for c in qualified_candidates if c.get("ticker", "").upper() not in retained_tickers]
    # Sort eligible candidates by discount distance to Max Pain descending
    eligible_candidates.sort(
        key=lambda c: float(c.get("discount_pct", 0.0)),
        reverse=True,
    )
    selected_buys = eligible_candidates[:open_slots]

    buys: list[dict[str, Any]] = []
    total_deployable_cash = available_cash + freed_cash
    remaining_cash = total_deployable_cash

    if selected_buys and total_deployable_cash > 0:
        alloc_per_buy = total_deployable_cash / len(selected_buys)
        for cand in selected_buys:
            ticker = cand["ticker"].upper()
            raw_price = float(cand.get("price", 0.0))
            if raw_price <= 0:
                continue

            exec_price = raw_price * (1.0 + slip_factor)
            shares = int(alloc_per_buy // exec_price)
            if shares <= 0:
                continue

            cost = shares * exec_price
            remaining_cash -= cost
            buys.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "execution_price": exec_price,
                    "total_cost": cost,
                    "target_strike": cand.get("max_pain_strike"),
                    "discount_pct": cand.get("discount_pct"),
                    "jev_confidence": cand.get("jev_confidence"),
                }
            )

    logger.info(
        f"Computed Max Pain rebalance: {len(sales)} sales (freed ${freed_cash:,.2f}), "
        f"{len(retained)} retained, {len(buys)} buys (cash remaining: ${remaining_cash:,.2f})"
    )

    return {
        "sales": sales,
        "retained": retained,
        "buys": buys,
        "freed_cash": freed_cash,
        "remaining_cash": remaining_cash,
    }


async def reconcile_unliquidated_max_pain_positions(
    portfolio_row: dict[str, Any],
    positions: list[dict[str, Any]],
    audit_date: str,
    client: Any,
    slippage_bps: float = DEFAULT_MAX_PAIN_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Post-close reconciliation for unliquidated 0DTE positions in sys-max-pain.

    Evaluates whether the regular trading session high touched the day's verified Max Pain
    strike (filling at the target strike) or held into the close (filling at RTH close),
    records BACKFILLED SELL trades, clears open positions, and updates portfolio equity.
    """
    from execution.providers.alpaca_max_pain import get_verified_max_pain
    from tasks.evaluate_daily_predictions import fetch_intraday_prices

    portfolio_id = str(portfolio_row["id"])
    current_cash = float(portfolio_row.get("cash_balance") or 0.0)
    slip_factor = slippage_bps / 10000.0
    freed_cash = 0.0
    exited: list[dict[str, Any]] = []

    for pos in positions:
        ticker = str(pos.get("ticker", "SPY")).upper()
        qty = int(pos.get("quantity") or 0)
        if qty <= 0:
            continue
        cost_basis = float(pos.get("average_cost_basis") or 0.0)
        raw_ts = str(pos.get("last_updated_at") or "")
        pos_date = raw_ts[:10] if len(raw_ts) >= 10 else audit_date

        _, high_p, _, close_p = await fetch_intraday_prices(ticker, pos_date)
        resolved_close = float(close_p) if close_p and float(close_p) > 0 else cost_basis
        resolved_high = float(high_p) if high_p and float(high_p) > 0 else resolved_close

        verified = await get_verified_max_pain(ticker, expiration_date=pos_date)
        target_strike = (
            float(verified["max_pain"])
            if verified and verified.get("max_pain") and float(verified["max_pain"]) > 0
            else cost_basis * 1.008
        )

        _, reason = evaluate_max_pain_holding_exit(
            {"ticker": ticker, "entry_price": cost_basis, "target_strike": target_strike},
            current_price=resolved_close,
            session_high=resolved_high,
            is_market_close_window=True,
        )
        raw_exit_p = (
            max(resolved_close, target_strike)
            if "pin achieved" in reason.lower() and target_strike > 0
            else resolved_close
        )
        exec_price = raw_exit_p * (1.0 - slip_factor)
        proceeds = qty * exec_price
        freed_cash += proceeds
        realized_pnl = (exec_price - cost_basis) * qty
        realized_pnl_pct = (((exec_price / cost_basis) - 1.0) * 100.0) if cost_basis > 0 else 0.0

        exit_trade = {
            "id": str(uuid4()),
            "portfolio_id": portfolio_id,
            "ticker": ticker,
            "signal": "SELL",
            "quantity": qty,
            "price": exec_price,
            "total_cost": proceeds,
            "realized_pnl": realized_pnl,
            "realized_pnl_pct": realized_pnl_pct,
            "alpaca_status": "BACKFILLED",
            "executed_at": f"{pos_date}T20:00:00Z",
        }
        client.table("trades").insert(exit_trade).execute()
        client.table("portfolio_positions").delete().eq("portfolio_id", portfolio_id).eq("ticker", ticker).execute()
        exited.append({"ticker": ticker, "shares": qty, "exit_price": exec_price, "reason": reason})

    new_cash = max(0.0, current_cash + freed_cash)
    client.table("portfolios").update(
        {
            "cash_balance": new_cash,
            "total_equity": new_cash,
            "realized": new_cash,
            "buying_power": new_cash,
            "excess_liquidity": new_cash,
            "last_updated_at": datetime.now(UTC).isoformat(),
        }
    ).eq("id", portfolio_id).execute()

    client.table("portfolio_performance").upsert(
        {
            "portfolio_id": portfolio_id,
            "date": audit_date,
            "total_equity": new_cash,
            "cash_balance": new_cash,
            "buying_power": new_cash,
            "sma": 0.0,
            "realized": new_cash,
        },
        on_conflict="portfolio_id,date",
    ).execute()

    return {"new_equity": new_cash, "exited": exited}
