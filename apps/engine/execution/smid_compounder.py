"""Small/Mid-Cap Quality Compounder Execution Engine.

System portfolio that executes the Zero-Ceiling compounder strategy:
1. Retains compounding winners regardless of market cap expansion.
2. Liquidates deteriorating holdings (unprofitable zombies, cash burn, debt distress).
3. Recycles freed cash and available cash into new top-ranked small-cap quality compounders.
"""

from typing import Any

from core.config import logger

SYS_SMID_COMPOUNDER_OWNER_ID = "sys-smid-quality-compounder"
DEFAULT_SLIPPAGE_BPS = 5.0
DEFAULT_TARGET_HOLDINGS = 25


def compute_smid_rebalance_orders(
    current_holdings: list[dict],
    holding_evaluations: dict[str, dict],
    candidate_pool: list[dict],
    available_cash: float,
    target_holdings_count: int = DEFAULT_TARGET_HOLDINGS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Computes liquidations, retentions, and new buy orders for the SMID compounder portfolio."""
    slip_factor = slippage_bps / 10000.0

    sales: list[dict] = []
    retained: list[dict] = []
    freed_cash = 0.0

    for holding in current_holdings:
        ticker = holding["ticker"]
        shares = int(holding.get("shares") or 0)
        current_p = float(holding.get("current_price") or 0.0)

        ev = holding_evaluations.get(ticker, {"should_sell": False, "reason": "hold_quality_winner"})
        if ev.get("should_sell"):
            exit_price = current_p * (1.0 - slip_factor)
            sale_value = shares * exit_price
            freed_cash += sale_value
            sales.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "execution_price": exit_price,
                    "sale_value": sale_value,
                    "reason": ev.get("reason", "fundamental_exit"),
                }
            )
            logger.info(f"SMID Compounder: Liquidating {ticker} ({shares} shares at {exit_price:.2f}). Reason: {ev.get('reason')}")
        else:
            retained.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "current_price": current_p,
                    "market_cap": holding.get("market_cap"),
                    "reason": ev.get("reason", "hold_quality_winner"),
                }
            )

    total_cash_for_reinvestment = available_cash + freed_cash
    open_slots = max(0, target_holdings_count - len(retained))

    buys: list[dict] = []
    remaining_cash = total_cash_for_reinvestment

    if open_slots > 0 and candidate_pool:
        # Filter candidates that are already retained in portfolio
        retained_tickers = {h["ticker"] for h in retained}
        new_candidates = [c for c in candidate_pool if c["symbol"] not in retained_tickers]

        slots_to_fill = min(open_slots, len(new_candidates))
        if slots_to_fill > 0:
            cash_per_slot = total_cash_for_reinvestment / slots_to_fill

            for cand in new_candidates[:slots_to_fill]:
                price = float(cand.get("price") or 0.0)
                if price <= 0:
                    continue

                entry_price = price * (1.0 + slip_factor)
                shares = int(cash_per_slot // entry_price)

                if shares > 0:
                    cost = shares * entry_price
                    buys.append(
                        {
                            "ticker": cand["symbol"],
                            "shares": shares,
                            "execution_price": entry_price,
                            "total_cost": cost,
                            "market_cap": cand.get("market_cap"),
                            "composite_score": cand.get("composite_score"),
                        }
                    )
                    remaining_cash -= cost
                    logger.info(f"SMID Compounder: Buying {cand['symbol']} ({shares} shares at {entry_price:.2f})")

    return {
        "sales": sales,
        "retained": retained,
        "freed_cash": freed_cash,
        "total_cash_for_reinvestment": total_cash_for_reinvestment,
        "buys": buys,
        "remaining_cash": remaining_cash,
    }
