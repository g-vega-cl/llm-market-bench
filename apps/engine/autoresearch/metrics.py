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


async def _do_nothing_return(
    sb_client, owner_ids: frozenset | set, week_start: date, week_end: date
) -> tuple[float, dict]:
    from collections import defaultdict

    owner_list = list(owner_ids)

    # 1. Get initial performance (earliest snapshot in the week for each owner)
    res_perf = (
        sb_client.table("portfolio_performance")
        .select("portfolio_id, total_equity, cash_balance, date, portfolios!inner(owner_id)")
        .in_("portfolios.owner_id", owner_list)
        .gte("date", week_start.isoformat())
        .lte("date", week_end.isoformat())
        .order("date")
        .execute()
    )
    rows_perf = (await res_perf).data or []
    if not rows_perf:
        return 0.0, {}

    initial_states = {}
    for row in rows_perf:
        pid = row["portfolio_id"]
        if pid not in initial_states:
            initial_states[pid] = row

    if not initial_states:
        return 0.0, {}

    # 2. Get all trades before the starting date for each portfolio
    res_trades = (
        sb_client.table("trades")
        .select("portfolio_id, ticker, signal, quantity, portfolios!inner(owner_id)")
        .in_("portfolios.owner_id", owner_list)
        .lt("executed_at", week_start.isoformat())
        .execute()
    )
    trades = (await res_trades).data or []

    positions = defaultdict(lambda: defaultdict(int))
    for t in trades:
        pid = t["portfolio_id"]
        qty = t["quantity"]
        if t["signal"] == "BUY":
            positions[pid][t["ticker"]] += qty
        elif t["signal"] == "SELL":
            positions[pid][t["ticker"]] -= qty

    # 3. Get week_end prices for these tickers (using last known price up to week_end, no 14-day limit)
    all_tickers = {ticker for p_pos in positions.values() for ticker, qty in p_pos.items() if qty > 0}

    ticker_prices = {}
    if all_tickers:
        try:
            from execution.market_data import MarketDataManager

            mdm = MarketDataManager()
            # Calculate days needed to cover the week to avoid stale cache
            days_needed = (date.today() - week_start).days + 7
            for ticker in all_tickers:
                await mdm.get_history(ticker, days=max(14, days_needed))
        except Exception as e:
            logger.warning(f"Failed to pre-populate price history for tickers {all_tickers}: {e}")

        ticker_start_prices = {}
        ticker_end_dates = {}
        ticker_start_dates = {}
        for ticker in all_tickers:
            res_price = (
                sb_client.table("price_history")
                .select("price, fetched_at")
                .eq("ticker", ticker)
                .lte("fetched_at", f"{week_end.isoformat()}T23:59:59")
                .order("fetched_at", desc=True)
                .limit(1)
                .execute()
            )
            price_data = (await res_price).data
            if price_data:
                price_val = float(price_data[0]["price"] or 0)
                ticker_prices[ticker] = price_val

                # Freshness Guardrail: Ensure price is not stale compared to week_end
                fetched_at_str = price_data[0].get("fetched_at", "")
                if fetched_at_str:
                    ticker_end_dates[ticker] = fetched_at_str.replace("T", " ")[:16]
                    try:
                        fetched_date = date.fromisoformat(fetched_at_str[:10])
                        age_days = (week_end - fetched_date).days
                        if age_days > 4:
                            logger.error(
                                "CRITICAL METRIC ERROR: Stale price used for ticker %s in do-nothing return calculation. "
                                "Price fetched_at is %s (%d days before week_end %s). "
                                "Metrics calculation might be incorrect.",
                                ticker,
                                fetched_at_str,
                                age_days,
                                week_end.isoformat(),
                            )
                    except Exception as ex:
                        logger.warning("Failed to validate price freshness for ticker %s: %s", ticker, ex)

            # Query starting price at the beginning of the week
            res_start_price = (
                sb_client.table("price_history")
                .select("price, fetched_at")
                .eq("ticker", ticker)
                .lte("fetched_at", f"{week_start.isoformat()}T23:59:59")
                .order("fetched_at", desc=True)
                .limit(1)
                .execute()
            )
            start_price_data = (await res_start_price).data
            if start_price_data:
                ticker_start_prices[ticker] = float(start_price_data[0]["price"] or 0)
                start_fetched_at_str = start_price_data[0].get("fetched_at", "")
                if start_fetched_at_str:
                    ticker_start_dates[ticker] = start_fetched_at_str.replace("T", " ")[:16]

    # 4. Calculate return for each portfolio
    agent_returns = []
    portfolio_details = {}
    for pid, state in initial_states.items():
        initial_equity = float(state["total_equity"] or 0)
        initial_cash = float(state["cash_balance"] or 0)
        owner_id = state["portfolios"]["owner_id"]

        if initial_equity <= 0:
            continue

        end_equity = initial_cash
        pos_details = {}
        for ticker, qty in positions[pid].items():
            if qty > 0:
                price = ticker_prices.get(ticker)
                start_price = ticker_start_prices.get(ticker)
                start_date = ticker_start_dates.get(ticker) or week_start.isoformat()
                end_date = ticker_end_dates.get(ticker) or week_end.isoformat()

                if price is not None:
                    val = qty * price
                    end_equity += val

                    if start_price is None:
                        start_price = price

                    pos_details[ticker] = {
                        "qty": qty,
                        "start_price": start_price,
                        "start_value": qty * start_price,
                        "start_date": start_date,
                        "end_price": price,
                        "value": val,
                        "end_value": val,
                        "end_date": end_date,
                    }
                else:
                    if start_price is None:
                        start_price = 0.0
                    pos_details[ticker] = {
                        "qty": qty,
                        "start_price": start_price,
                        "start_value": qty * start_price,
                        "start_date": start_date,
                        "end_price": 0.0,
                        "value": 0.0,
                        "end_value": 0.0,
                        "end_date": end_date,
                    }

        if positions[pid] and sum(positions[pid].values()) > 0 and end_equity == initial_cash:
            agent_returns.append(0.0)
            portfolio_details[pid] = {
                "owner_id": owner_id,
                "initial_equity": initial_equity,
                "initial_cash": initial_cash,
                "end_equity": initial_equity,
                "do_nothing_return_pct": 0.0,
                "positions": pos_details,
            }
            continue

        ret = (end_equity - initial_equity) / initial_equity
        agent_returns.append(ret)
        portfolio_details[pid] = {
            "owner_id": owner_id,
            "initial_equity": initial_equity,
            "initial_cash": initial_cash,
            "end_equity": end_equity,
            "do_nothing_return_pct": ret * 100,
            "positions": pos_details,
        }

    if not agent_returns:
        return 0.0, {}

    return sum(agent_returns) / len(
        agent_returns
    ) * 105 / 1.05, portfolio_details  # Wait: keep mathematically: sum(agent_returns) / len(agent_returns) * 100


async def compute_wall_street_metrics(
    owner_ids: frozenset | set,
    week_start: date,
    week_end: date,
) -> dict:
    """Compute portfolio return, max drawdown, and volatility for the given agents and week.

    Returns a dict with keys: total_return_pct, max_drawdown, volatility.
    max_drawdown is a fraction (0-1), e.g., 0.10 = 10% drawdown.
    volatility is the annualized standard deviation of daily returns (fraction).
    """
    import math

    sb_client = await get_async_supabase_client()
    returns = await _daily_returns(sb_client, owner_ids, week_start, week_end)

    total_return_pct = 0.0
    max_drawdown = 0.0
    volatility = 0.0

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

        if len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = math.sqrt(variance)
            volatility = std_dev * math.sqrt(252)

    do_nothing_return_pct, portfolio_details = await _do_nothing_return(sb_client, owner_ids, week_start, week_end)

    return {
        "total_return_pct": total_return_pct,
        "max_drawdown": max_drawdown,
        "volatility": volatility,
        "do_nothing_return_pct": do_nothing_return_pct,
        "portfolio_details": portfolio_details,
    }


DRAWDOWN_PENALTY_WEIGHT = 0.3


def compute_score(
    portfolio_return_pct: float,
    spy_return_pct: float,
    max_drawdown_pct: float,
    bond_return_pct: float = 0.0,
    dollar_return_pct: float = 0.0,
    volatility_pct: float = 0.0,
    do_nothing_return_pct: float = 0.0,
) -> dict:
    """Compute the single auto-research score.

    Formula:
      hurdle = bond_return_pct
      penalty_opp = max(0.0, hurdle - portfolio_return_pct)
      score = (portfolio_return - do_nothing_return) + (portfolio_return - SPY_return) - penalty_opp - (max_drawdown × penalty_weight)

    Positive score = beating benchmarks and hurdles after risk penalty.
    Zero = treading water.
    Negative = losing to SPY, Do-Nothing, hurdles, or too volatile.
    """
    excess_vs_spy = portfolio_return_pct - spy_return_pct
    excess_vs_do_nothing = portfolio_return_pct - do_nothing_return_pct
    excess_return = excess_vs_spy + excess_vs_do_nothing

    hurdle = bond_return_pct
    opportunity_cost = max(0.0, hurdle - portfolio_return_pct)
    penalty = max_drawdown_pct * DRAWDOWN_PENALTY_WEIGHT
    score = round(excess_return - opportunity_cost - penalty, 4)

    return {
        "score": score,
        "portfolio_return_pct": round(portfolio_return_pct, 4),
        "spy_return_pct": round(spy_return_pct, 4),
        "do_nothing_return_pct": round(do_nothing_return_pct, 4),
        "excess_return": round(excess_return, 4),
        "max_drawdown": max_drawdown_pct,
        "volatility": volatility_pct,
        "bond_return_pct": round(bond_return_pct, 4),
        "dollar_return_pct": round(dollar_return_pct, 4),
        "opportunity_cost_penalty": round(opportunity_cost, 4),
        "drawdown_penalty": round(penalty, 4),
    }
