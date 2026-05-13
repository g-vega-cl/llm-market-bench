"""Metrics computation for auto-research evaluation.

Computes portfolio return and max drawdown from portfolio_performance data.
`compute_score` combines these with SPY return into a single risk-adjusted score.
"""

import logging
from datetime import date

from core.db import get_async_supabase_client

logger = logging.getLogger("engine")


async def _daily_returns(sb_client, owner_ids: frozenset | set, week_start: date, week_end: date) -> list[float]:
    """Extract daily equity returns for experiment agents in the given week.

    Joins portfolio_performance with portfolios to filter by owner_id.
    """
    owner_list = list(owner_ids)
    res = (
        sb_client.table("portfolio_performance")
        .select("date, total_equity, portfolios!inner(owner_id)")
        .in_("portfolios.owner_id", owner_list)
        .gte("date", week_start.isoformat())
        .lte("date", week_end.isoformat())
        .order("date")
        .execute()
    )
    rows = (await res).data or []
    if len(rows) < 2:
        return []

    # Aggregate equity across agents per day
    daily_equity: dict[str, float] = {}
    for row in rows:
        d = row["date"]
        eq = float(row["total_equity"] or 0)
        daily_equity[d] = daily_equity.get(d, 0) + eq

    sorted_dates = sorted(daily_equity.keys())
    returns = []
    for i in range(1, len(sorted_dates)):
        prev = daily_equity[sorted_dates[i - 1]]
        curr = daily_equity[sorted_dates[i]]
        if prev > 0:
            returns.append((curr - prev) / prev)
    return returns


async def _spy_returns(sb_client, week_start: date, week_end: date) -> list[float]:
    """Extract daily SPY returns for benchmark comparison."""
    res = (
        sb_client.table("price_history")
        .select("fetched_at, price")
        .eq("ticker", "SPY")
        .gte("fetched_at", week_start.isoformat())
        .lte("fetched_at", f"{week_end.isoformat()}T23:59:59")
        .order("fetched_at")
        .execute()
    )
    rows = (await res).data or []
    if len(rows) < 2:
        return []
    returns = []
    for i in range(1, len(rows)):
        prev = float(rows[i - 1]["price"] or 0)
        curr = float(rows[i]["price"] or 0)
        if prev > 0:
            returns.append((curr - prev) / prev)
    return returns


async def compute_wall_street_metrics(
    owner_ids: frozenset | set,
    week_start: date,
    week_end: date,
) -> dict:
    """Compute portfolio return and max drawdown for the given agents and week.

    Returns a dict with keys: total_return_pct, max_drawdown.
    max_drawdown is a fraction (0-1), e.g., 0.10 = 10% drawdown.
    """
    sb_client = await get_async_supabase_client()
    returns = await _daily_returns(sb_client, owner_ids, week_start, week_end)

    total_return_pct = 0.0
    max_drawdown = 0.0

    if returns:
        cumulative = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in returns:
            cumulative *= (1 + r)
            if cumulative > peak:
                peak = cumulative
            dd = (cumulative - peak) / peak
            if dd < max_dd:
                max_dd = dd
        max_drawdown = abs(max_dd)
        total_return_pct = (cumulative - 1) * 100

    return {
        "total_return_pct": total_return_pct,
        "max_drawdown": max_drawdown,
    }


DRAWDOWN_PENALTY_WEIGHT = 0.3


def compute_score(
    portfolio_return_pct: float,
    spy_return_pct: float,
    max_drawdown_pct: float,
) -> dict:
    """Compute the single auto-research score.

    Formula: score = (portfolio_return - SPY_return) - (max_drawdown × penalty_weight)

    Positive score = beating SPY after risk penalty.
    Zero = treading water.
    Negative = losing to SPY or too volatile.
    """
    excess_return = portfolio_return_pct - spy_return_pct
    penalty = max_drawdown_pct * DRAWDOWN_PENALTY_WEIGHT
    score = round(excess_return - penalty, 4)

    return {
        "score": score,
        "excess_return": round(excess_return, 4),
        "max_drawdown": max_drawdown_pct,
    }
