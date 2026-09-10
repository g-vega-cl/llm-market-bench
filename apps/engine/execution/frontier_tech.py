"""Frontier Technology Supercycle Execution Engine.

Executes the venture-style power-law basket for sys-frontier-tech:
1. Retains long-term holdings through multi-year volatility without tight stop-losses.
2. Liquidates only on fundamental thesis death (insolvency, delisting, thesis canceled).
3. Allocates 2% to 4% (default 3%) per qualified small-cap pure-play across approved themes.
"""

from typing import Any

from analytics.frontier_tech import evaluate_thesis_death
from core.config import logger

SYS_FRONTIER_TECH_OWNER_ID = "sys-frontier-tech"
DEFAULT_SLIPPAGE_BPS = 5.0  # 5 bps = 0.05%
DEFAULT_TARGET_POSITION_WEIGHT = 0.03  # 3% per position


def compute_frontier_rebalance_orders(
    current_holdings: list[dict[str, Any]],
    current_cash: float,
    total_equity: float,
    candidate_stocks: list[dict[str, Any]],
    target_weight: float = DEFAULT_TARGET_POSITION_WEIGHT,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Computes liquidations, retentions, and new buy allocations for sys-frontier-tech.

    Enforces:
    - Minimal churn: holdings are retained unless thesis death occurs.
    - Sizing: Target allocation 2% to 4% of total equity.
    - Slippage friction: applied to entries and exits.
    """
    slip_factor = slippage_bps / 10000.0

    sales: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    freed_cash = 0.0

    # 1. Process current holdings
    for holding in current_holdings:
        ticker = holding["ticker"]
        shares = int(holding.get("shares") or holding.get("quantity") or 0)
        current_p = float(holding.get("current_price") or holding.get("price") or 0.0)

        status_flag = holding.get("status")
        should_exit = status_flag == "thesis_death"
        exit_reason = "thesis_death" if should_exit else ""

        if not should_exit:
            should_exit, exit_reason = evaluate_thesis_death(holding)

        if should_exit:
            exit_price = current_p * (1.0 - slip_factor)
            sale_value = shares * exit_price
            freed_cash += sale_value
            sales.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "execution_price": exit_price,
                    "sale_value": sale_value,
                    "reason": exit_reason or "fundamental_exit",
                }
            )
            logger.info(
                f"Frontier Tech: Liquidating {ticker} ({shares} shares at {exit_price:.2f}). Reason: {exit_reason}"
            )
        else:
            retained.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "current_price": current_p,
                    "theme": holding.get("theme", "Frontier"),
                }
            )

    # 2. Process new buys from candidate pool
    buys: list[dict[str, Any]] = []
    deployable_cash = current_cash + freed_cash
    retained_tickers = {h["ticker"] for h in retained}
    target_dollars = total_equity * target_weight

    for candidate in candidate_stocks:
        ticker = candidate["ticker"]
        if ticker in retained_tickers:
            continue

        raw_price = float(candidate.get("price") or 0.0)
        if raw_price <= 0.0:
            continue

        exec_price = raw_price * (1.0 + slip_factor)
        needed_dollars = min(target_dollars, deployable_cash)
        shares = int(needed_dollars / exec_price)

        if shares > 0 and (shares * exec_price) <= deployable_cash:
            order_cost = shares * exec_price
            deployable_cash -= order_cost
            buys.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "execution_price": exec_price,
                    "order_value": order_cost,
                    "theme": candidate.get("theme", "Frontier"),
                }
            )
            retained_tickers.add(ticker)
            logger.info(
                f"Frontier Tech: Buying {ticker} ({shares} shares at {exec_price:.2f} for {candidate.get('theme')})"
            )

    return {
        "sales": sales,
        "retained": retained,
        "buys": buys,
        "freed_cash": freed_cash,
        "remaining_cash": deployable_cash,
    }
