"""Wall Street metrics computation for auto-research evaluation.

Computes Sharpe, Sortino, Information Ratio, Maximum Drawdown, and Profit
Factor from portfolio_performance and trades tables. `compute_wall_street_metrics`
returns raw values; `compute_composite_score` is the only function that
normalizes to 0-1 and combines them into a single score.
"""

import logging
from datetime import date
from math import sqrt

from core.db import get_async_supabase_client

logger = logging.getLogger("engine")

TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.05


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
    """Extract daily SPY returns for Information Ratio benchmark."""
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


async def _realized_pnl(sb_client, owner_ids: frozenset | set, week_start: date, week_end: date) -> tuple[float, float]:
    """Compute gross profit and gross loss from realized SELL trades."""
    owner_list = list(owner_ids)
    res = (
        sb_client.table("trades")
        .select("realized_pnl, portfolios!inner(owner_id)")
        .in_("portfolios.owner_id", owner_list)
        .eq("signal", "SELL")
        .gte("executed_at", week_start.isoformat())
        .lte("executed_at", f"{week_end.isoformat()}T23:59:59")
        .execute()
    )
    gross_profit = 0.0
    gross_loss = 0.0
    for row in ((await res).data or []):
        pnl = float(row.get("realized_pnl") or 0)
        if pnl > 0:
            gross_profit += pnl
        else:
            gross_loss += abs(pnl)
    return gross_profit, gross_loss


async def compute_wall_street_metrics(
    owner_ids: frozenset | set,
    week_start: date,
    week_end: date,
    spy_returns: list[float] | None = None,
) -> dict:
    """Compute all Wall Street metrics for the given agents and week.

    Args:
        owner_ids: Portfolio owner IDs to evaluate.
        week_start, week_end: Evaluation window.
        spy_returns: Pre-fetched SPY daily returns for Information Ratio.
                     If None, fetched internally. Pass to avoid duplicate
                     API calls when evaluating multiple agent groups.

    Returns a dict with keys: sharpe, sortino, max_drawdown, profit_factor,
    info_ratio, and their raw (unnormalized) values for the report.
    """
    sb_client = await get_async_supabase_client()
    returns = await _daily_returns(sb_client, owner_ids, week_start, week_end)
    if spy_returns is None:
        spy_returns = await _spy_returns(sb_client, week_start, week_end)
    gross_profit, gross_loss = await _realized_pnl(sb_client, owner_ids, week_start, week_end)

    metrics = {
        "sharpe": 0.0,
        "sortino": 0.0,
        "max_drawdown": 0.0,
        "profit_factor": 0.0,
        "info_ratio": 0.0,
        "num_trading_days": len(returns),
        "total_return_pct": 0.0,
    }

    if returns:
        mean_daily = sum(returns) / len(returns)
        variance = sum((r - mean_daily) ** 2 for r in returns) / (len(returns) - 1) if len(returns) > 1 else 0
        std_daily = sqrt(variance) if variance > 0 else 0
        excess_daily = mean_daily - (RISK_FREE_RATE / TRADING_DAYS_PER_YEAR)

        if std_daily > 0:
            metrics["sharpe"] = (excess_daily / std_daily) * sqrt(TRADING_DAYS_PER_YEAR)

        downside_returns = [r for r in returns if r < 0]
        if downside_returns:
            downside_mean = sum(downside_returns) / len(downside_returns)
            downside_var = sum((r - downside_mean) ** 2 for r in downside_returns) / (len(downside_returns) - 1) if len(downside_returns) > 1 else 0
            downside_std = sqrt(downside_var) if downside_var > 0 else 0
            if downside_std > 0:
                metrics["sortino"] = (excess_daily / downside_std) * sqrt(TRADING_DAYS_PER_YEAR)
        else:
            metrics["sortino"] = 999.0

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
        metrics["max_drawdown"] = abs(max_dd)
        metrics["total_return_pct"] = (cumulative - 1) * 100

    if gross_loss > 0:
        metrics["profit_factor"] = gross_profit / gross_loss
    elif gross_profit > 0:
        metrics["profit_factor"] = 999.0

    if returns and spy_returns:
        aligned = min(len(returns), len(spy_returns))
        excess = [returns[i] - spy_returns[i] for i in range(aligned)]
        if len(excess) > 1:
            mean_excess = sum(excess) / len(excess)
            te_var = sum((e - mean_excess) ** 2 for e in excess) / (len(excess) - 1)
            te = sqrt(te_var) if te_var > 0 else 0
            if te > 0:
                metrics["info_ratio"] = (mean_excess / te) * sqrt(TRADING_DAYS_PER_YEAR)

    return metrics


def _normalize_sharpe(sharpe: float) -> float:
    """Normalize Sharpe to 0-1. Cap at -2 to 5 range."""
    return max(0.0, min(1.0, (sharpe + 2) / 7))


def _normalize_sortino(sortino: float) -> float:
    """Normalize Sortino to 0-1. Cap at -2 to 5 range."""
    return max(0.0, min(1.0, (sortino + 2) / 7))


def _normalize_drawdown(dd: float) -> float:
    """Normalize max drawdown to 0-1 (inverted: 0 drawdown = 1, 50%+ = 0)."""
    return max(0.0, 1.0 - dd / 0.50)


def _normalize_profit_factor(pf: float) -> float:
    """Normalize profit factor to 0-1. 1 = break-even = 0.5, 3+ = 1."""
    if pf >= 3:
        return 1.0
    if pf <= 0:
        return 0.0
    return (pf - 0.5) / 2.5


def _normalize_info_ratio(ir: float) -> float:
    """Normalize Info Ratio to 0-1. Cap at -2 to 5 range."""
    return max(0.0, min(1.0, (ir + 2) / 7))


def compute_composite_score(
    wall_street: dict,
    concordance: float = 0.0,
    conviction: float = 0.0,
    regime_awareness: float = 0.0,
) -> dict:
    """Compute a composite score from all evaluation dimensions.

    Returns dict with composite and breakdown of sub-scores.
    """
    s_sharpe = _normalize_sharpe(wall_street.get("sharpe", 0))
    s_sortino = _normalize_sortino(wall_street.get("sortino", 0))
    s_drawdown = _normalize_drawdown(wall_street.get("max_drawdown", 0))
    s_profit = _normalize_profit_factor(wall_street.get("profit_factor", 0))
    s_info = _normalize_info_ratio(wall_street.get("info_ratio", 0))

    composite = (
        0.15 * s_sharpe
        + 0.15 * s_sortino
        + 0.15 * s_drawdown
        + 0.15 * s_profit
        + 0.10 * s_info
        + 0.10 * concordance
        + 0.10 * conviction
        + 0.10 * regime_awareness
    )

    warnings = []
    if wall_street.get("num_trading_days", 0) == 0:
        warnings.append("NO_TRADING_DATA: no daily returns for this week (composite may be unreliable)")
    if wall_street.get("info_ratio", 0) == 0:
        warnings.append("NO_BENCHMARK: SPY benchmark data unavailable (Information Ratio excluded)")

    return {
        "composite": round(composite, 4),
        "sharpe_normalized": round(s_sharpe, 4),
        "sortino_normalized": round(s_sortino, 4),
        "drawdown_normalized": round(s_drawdown, 4),
        "profit_factor_normalized": round(s_profit, 4),
        "info_ratio_normalized": round(s_info, 4),
        "concordance": round(concordance, 4),
        "conviction_calibration": round(conviction, 4),
        "regime_awareness": round(regime_awareness, 4),
        "warnings": warnings,
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
