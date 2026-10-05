"""Post-Earnings Announcement Drift (PEAD) systematic portfolio execution logic.

Handles:
1. Evaluating holding exits (30 trading days expiration, 5% trailing ATR stop).
2. Sizing and capital allocation for top-decile SUE candidates admitted by Jev.
3. Generating execution rebalance orders with transaction slippage.
"""

from typing import Any

from core.config import logger

SYS_PEAD_DRIFT_OWNER_ID = "sys-pead-drift"
DEFAULT_MAX_HOLDINGS = 12
DEFAULT_MAX_HOLDING_DAYS = 30
DEFAULT_SLIPPAGE_BPS = 5.0  # 5 bps = 0.05%
DEFAULT_TRAILING_STOP_PCT = 5.0


def evaluate_holding_exit(
    holding_info: dict[str, Any],
    current_price: float,
    max_holding_days: int = DEFAULT_MAX_HOLDING_DAYS,
    trailing_stop_pct: float = DEFAULT_TRAILING_STOP_PCT,
) -> tuple[bool, str]:
    """Evaluate whether an existing PEAD holding should be exited.

    Exit Triggers:
    1. Maximum holding horizon exceeded (empirical drift window expiration).
    2. Trailing stop triggered (drawdown from peak exceeds threshold).
    """
    holding_days = int(holding_info.get("holding_days", 0))
    if holding_days > max_holding_days:
        return True, f"Holding horizon expired ({holding_days}d > {max_holding_days}d)"

    peak_price = float(holding_info.get("peak_price", 0.0) or holding_info.get("entry_price", 0.0))
    if current_price > peak_price:
        peak_price = current_price

    if peak_price > 0 and current_price > 0:
        drawdown_pct = ((peak_price - current_price) / peak_price) * 100.0
        if drawdown_pct >= trailing_stop_pct:
            return True, f"Trailing stop triggered (-{drawdown_pct:.1f}% from peak ${peak_price:.2f})"

    return False, "Holding criteria healthy"


def compute_pead_rebalance_orders(
    current_holdings: list[dict[str, Any]],
    holding_evaluations: dict[str, dict[str, Any]],
    qualified_candidates: list[dict[str, Any]],
    available_cash: float,
    max_holdings: int = DEFAULT_MAX_HOLDINGS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Computes exact sales and buy orders for the PEAD portfolio."""
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
            exec_price = raw_price * (1.0 - slip_factor)
            proceeds = shares * exec_price
            freed_cash += proceeds
            sales.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "execution_price": exec_price,
                    "proceeds": proceeds,
                    "reason": eval_res.get("reason", "Exit rule satisfied"),
                }
            )
        else:
            retained.append(h)

    # 2. Determine open slots and candidate selection
    open_slots = max(0, max_holdings - len(retained))
    retained_tickers = {h["ticker"].upper() for h in retained}

    eligible_candidates = [c for c in qualified_candidates if c.get("ticker", "").upper() not in retained_tickers]
    # Sort eligible candidates by SUE score descending
    eligible_candidates.sort(key=lambda c: float(c.get("sue_score", 0.0)), reverse=True)
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
                    "sue_score": cand.get("sue_score"),
                    "jev_confidence": cand.get("jev_confidence"),
                }
            )

    logger.info(
        f"Computed PEAD rebalance: {len(sales)} sales (freed ${freed_cash:,.2f}), "
        f"{len(retained)} retained, {len(buys)} buys (cash remaining: ${remaining_cash:,.2f})"
    )

    return {
        "sales": sales,
        "retained": retained,
        "buys": buys,
        "freed_cash": freed_cash,
        "remaining_cash": remaining_cash,
    }
