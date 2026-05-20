"""Metrics computation for auto-research evaluation.

Computes portfolio return and max drawdown from portfolio_performance data.
`compute_score` combines these with SPY return into a single risk-adjusted score.
"""

import logging
from datetime import date

from core.db import get_async_supabase_client

logger = logging.getLogger("engine")


async def _daily_returns(sb_client, owner_ids: frozenset | set, week_start: date, week_end: date) -> list[float]:
    """Extract daily percentage returns, equal-weighted across agents.

    Each agent's daily returns are computed independently from its own
    equity curve, then averaged per day. A $10K portfolio and a $5K
    portfolio have equal weight — only percentage changes matter.

    Returns a list of averaged daily returns (one float per day gap).
    """
    from collections import defaultdict

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

    # Group equity by (owner_id, date)
    agent_equity: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        owner = row["portfolios"]["owner_id"]
        d = row["date"]
        eq = float(row["total_equity"] or 0)
        agent_equity[owner][d] = eq

    # All unique dates across all agents, sorted
    all_dates = sorted({row["date"] for row in rows})

    # For each day gap, compute per-agent returns, then average
    returns = []
    for i in range(1, len(all_dates)):
        prev_date = all_dates[i - 1]
        curr_date = all_dates[i]

        agent_daily_returns = []
        for _owner, equity_by_date in agent_equity.items():
            prev_eq = equity_by_date.get(prev_date)
            curr_eq = equity_by_date.get(curr_date)
            if prev_eq is not None and curr_eq is not None and prev_eq > 0:
                agent_daily_returns.append((curr_eq - prev_eq) / prev_eq)

        if agent_daily_returns:
            avg_return = sum(agent_daily_returns) / len(agent_daily_returns)
            returns.append(avg_return)

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
            cumulative *= 1 + r
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
    bond_return_pct: float = 0.0,
    dollar_return_pct: float = 0.0,
) -> dict:
    """Compute the single auto-research score.

    Formula:
      hurdle = bond_return_pct
      penalty_opp = max(0.0, hurdle - portfolio_return_pct)
      score = (portfolio_return - SPY_return) - penalty_opp - (max_drawdown × penalty_weight)

    Positive score = beating benchmarks and hurdles after risk penalty.
    Zero = treading water.
    Negative = losing to SPY, hurdles, or too volatile.
    """
    excess_return = portfolio_return_pct - spy_return_pct
    hurdle = bond_return_pct
    opportunity_cost = max(0.0, hurdle - portfolio_return_pct)
    penalty = max_drawdown_pct * DRAWDOWN_PENALTY_WEIGHT
    score = round(excess_return - opportunity_cost - penalty, 4)

    return {
        "score": score,
        "excess_return": round(excess_return, 4),
        "max_drawdown": max_drawdown_pct,
        "bond_return_pct": round(bond_return_pct, 4),
        "dollar_return_pct": round(dollar_return_pct, 4),
        "opportunity_cost_penalty": round(opportunity_cost, 4),
    }
