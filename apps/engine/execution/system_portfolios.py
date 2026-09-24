"""System Portfolios Module.

Executes mechanical / rule-based portfolios that do not require independent LLM reasoning:
1. Strategy 1 (Weekly Sector Long/Short): Equal-weighted long best sector predictions and short worst sector predictions.
2. Strategy 2 (Daily S&P Intraday Trader): Systematic 100% equity day trading on SPY based on daily open-to-close predictions.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from core.config import logger
from core.db import get_supabase_client
from execution.daily_trading import (
    DEFAULT_DAILY_CLOSE_SLIPPAGE_BPS as DEFAULT_DAILY_CLOSE_SLIPPAGE_BPS,
)
from execution.daily_trading import (
    DEFAULT_DAILY_SLIPPAGE_BPS as DEFAULT_DAILY_SLIPPAGE_BPS,
)
from execution.daily_trading import (
    SYS_DAILY_SPY_CLOSE_OWNER_PREFIX as SYS_DAILY_SPY_CLOSE_OWNER_PREFIX,
)
from execution.daily_trading import (
    SYS_DAILY_SPY_OWNER_PREFIX as SYS_DAILY_SPY_OWNER_PREFIX,
)
from execution.daily_trading import (
    compute_daily_trade_execution as compute_daily_trade_execution,
)
from execution.daily_trading import (
    execute_daily_spy_trade,
)
from execution.portfolio import Portfolio

SYS_SECTOR_LS_OWNER_ID = "sys-sector-ls-consensus"
SYS_SECTOR_LS_30D_OWNER_ID = "sys-sector-ls-30d"
SYS_SECTOR_LS_90D_OWNER_ID = "sys-sector-ls-90d"
ALL_SECTOR_LS_OWNER_IDS = [
    SYS_SECTOR_LS_OWNER_ID,
    SYS_SECTOR_LS_30D_OWNER_ID,
    SYS_SECTOR_LS_90D_OWNER_ID,
]
SYS_SECTOR_UNCORR_20D_OWNER_ID = "sys-sector-uncorr-20d"
SYS_SECTOR_UNCORR_7D_OWNER_ID = "sys-sector-uncorr-7d"
SYS_SECTOR_NAIVE_MOM_OWNER_ID = "sys-sector-naive-momentum"
SYS_SECTOR_MEAN_REV_OWNER_ID = "sys-sector-mean-reversion"
MECHANICAL_SECTOR_OWNER_IDS = [
    SYS_SECTOR_UNCORR_20D_OWNER_ID,
    SYS_SECTOR_UNCORR_7D_OWNER_ID,
    SYS_SECTOR_NAIVE_MOM_OWNER_ID,
    SYS_SECTOR_MEAN_REV_OWNER_ID,
]
MECHANICAL_SECTOR_UNIVERSE = [
    "XLK",
    "SMH",
    "XLE",
    "XLF",
    "XLV",
    "XLY",
    "XLI",
    "XLB",
    "XLU",
    "XLRE",
    "XLC",
    "XOP",
    "XME",
    "XBI",
]
SYS_SECTOR_START_DATE = "2026-08-17"
DEFAULT_SLIPPAGE_BPS = 5.0  # 5 bps = 0.05%
INITIAL_PORTFOLIO_CASH = 10000.00


async def execute_system_daily_trade(
    prediction: dict,
    intraday_data: dict,
    slippage_bps: float = DEFAULT_DAILY_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Wrapper delegating to daily_trading while honoring system_portfolios mock patches."""
    return await execute_daily_spy_trade(
        prediction=prediction,
        intraday_data=intraday_data,
        owner_prefix=SYS_DAILY_SPY_OWNER_PREFIX,
        exit_on_target=True,
        slippage_bps=slippage_bps,
        get_supabase_client_fn=get_supabase_client,
        get_or_create_system_portfolio_fn=get_or_create_system_portfolio,
    )


async def execute_system_daily_close_trade(
    prediction: dict,
    intraday_data: dict,
    slippage_bps: float = DEFAULT_DAILY_CLOSE_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Wrapper delegating to daily_trading while honoring system_portfolios mock patches."""
    return await execute_daily_spy_trade(
        prediction=prediction,
        intraday_data=intraday_data,
        owner_prefix=SYS_DAILY_SPY_CLOSE_OWNER_PREFIX,
        exit_on_target=False,
        slippage_bps=slippage_bps,
        get_supabase_client_fn=get_supabase_client,
        get_or_create_system_portfolio_fn=get_or_create_system_portfolio,
    )


def resolve_sector_predictions(predictions: list[dict]) -> tuple[list[str], list[str]]:
    """Extract and deduplicate best and worst sector predictions with conflict netting.

    If a ticker is predicted as best by one model and worst by another, it is
    cancelled out (dropped from both sides).
    """
    long_set: set[str] = set()
    short_set: set[str] = set()

    for pred in predictions:
        best_sec = (pred.get("predicted_sector") or "").strip().upper()
        worst_sec = (pred.get("predicted_worst_sector") or "").strip().upper()

        if best_sec and best_sec != "UNKNOWN":
            long_set.add(best_sec)

        if worst_sec and worst_sec != "UNKNOWN":
            short_set.add(worst_sec)

    # Net out conflicts (tickers appearing in both sets)
    conflicts = long_set.intersection(short_set)
    clean_longs = sorted(list(long_set - conflicts))
    clean_shorts = sorted(list(short_set - conflicts))

    return clean_longs, clean_shorts


def resolve_horizon_predictions(predictions: list[dict], timeframe: str) -> list[dict]:
    """Filter predictions to only those matching the specified forecast horizon timeframe."""
    return [p for p in predictions if (p.get("timeframe") or "").strip().lower() == timeframe.strip().lower()]


def resolve_mechanical_sectors(
    correlation_rows: list[dict],
    universe: list[str],
) -> dict[str, list[str]]:
    """Select target sector ETF pairs for each of the 4 mechanical sector benchmark strategies.

    Args:
        correlation_rows: Rows from correlation_data with ticker_a, ticker_b, pearson_corr, returns_a_7d, etc.
        universe: Set or list of eligible sector ETF tickers.

    Returns:
        Dictionary mapping portfolio owner_id to a list of target sector ETF tickers.
    """
    normalized_universe = {s.upper() for s in universe}

    returns_7d: dict[str, float] = {}
    returns_30d: dict[str, float] = {}
    correlations: dict[tuple[str, str], float] = {}

    for row in correlation_rows:
        a = (row.get("ticker_a") or "").upper()
        b = (row.get("ticker_b") or "").upper()
        if a not in normalized_universe or b not in normalized_universe:
            continue

        if row.get("returns_a_7d") is not None and a not in returns_7d:
            returns_7d[a] = float(row["returns_a_7d"])
        if row.get("returns_b_7d") is not None and b not in returns_7d:
            returns_7d[b] = float(row["returns_b_7d"])

        if row.get("returns_a_30d") is not None and a not in returns_30d:
            returns_30d[a] = float(row["returns_a_30d"])
        if row.get("returns_b_30d") is not None and b not in returns_30d:
            returns_30d[b] = float(row["returns_b_30d"])

        corr = row.get("pearson_corr")
        if corr is not None:
            correlations[(a, b)] = float(corr)
            correlations[(b, a)] = float(corr)

    # Helper to find best pair given return metric and correlation cutoff
    def get_uncorrelated_pair(rets: dict[str, float], max_abs_corr: float = 0.3) -> list[str]:
        eligible_tickers = [t for t in normalized_universe if t in rets]
        pairs = []
        for i in range(len(eligible_tickers)):
            for j in range(i + 1, len(eligible_tickers)):
                t1, t2 = eligible_tickers[i], eligible_tickers[j]
                c = correlations.get((t1, t2))
                if c is not None:
                    avg_ret = (rets[t1] + rets[t2]) / 2.0
                    pairs.append({"tickers": [t1, t2], "corr": c, "abs_corr": abs(c), "avg_ret": avg_ret})

        if not pairs:
            # Fallback to top 2 by return
            sorted_t = sorted(eligible_tickers, key=lambda t: rets[t], reverse=True)
            return sorted_t[:2]

        uncorr = [p for p in pairs if p["abs_corr"] < max_abs_corr]
        if not uncorr:
            # Fallback to least correlated pair
            least_corr = sorted(pairs, key=lambda p: p["abs_corr"])[0]
            return least_corr["tickers"]

        # Sort by average return descending
        uncorr.sort(key=lambda p: p["avg_ret"], reverse=True)
        return uncorr[0]["tickers"]

    # 1. Uncorrelated 20d/30d
    p_uncorr_20d = get_uncorrelated_pair(returns_30d, max_abs_corr=0.3)

    # 2. Uncorrelated 7d
    p_uncorr_7d = get_uncorrelated_pair(returns_7d, max_abs_corr=0.3)

    # 3. Naive Momentum (any corr, top 2 by 30d)
    avail_30d = [t for t in normalized_universe if t in returns_30d]
    sorted_30d = sorted(avail_30d, key=lambda t: returns_30d[t], reverse=True)
    p_naive_mom = sorted_30d[:2]

    # 4. Mean Reversion (bottom 2 by 7d, oversold bounce)
    avail_7d = [t for t in normalized_universe if t in returns_7d]
    sorted_7d = sorted(avail_7d, key=lambda t: returns_7d[t], reverse=False)
    p_mean_rev = sorted_7d[:2]

    return {
        SYS_SECTOR_UNCORR_20D_OWNER_ID: p_uncorr_20d,
        SYS_SECTOR_UNCORR_7D_OWNER_ID: p_uncorr_7d,
        SYS_SECTOR_NAIVE_MOM_OWNER_ID: p_naive_mom,
        SYS_SECTOR_MEAN_REV_OWNER_ID: p_mean_rev,
    }


async def get_or_create_system_portfolio(owner_id: str) -> Portfolio:
    """Load an existing system portfolio or initialize a new one in Supabase."""
    portfolio = Portfolio(owner_id)
    await portfolio.initialize()
    if not portfolio.id:
        client = get_supabase_client()
        res = (
            client.table("portfolios")
            .insert(
                {
                    "owner_id": owner_id,
                    "cash_balance": INITIAL_PORTFOLIO_CASH,
                    "sma": 0.0,
                    "total_equity": INITIAL_PORTFOLIO_CASH,
                    "realized": INITIAL_PORTFOLIO_CASH,
                    "buying_power": INITIAL_PORTFOLIO_CASH * 4,
                    "excess_liquidity": INITIAL_PORTFOLIO_CASH,
                }
            )
            .execute()
        )
        if res.data:
            portfolio.id = UUID(res.data[0]["id"])
            portfolio.cash_balance = INITIAL_PORTFOLIO_CASH
    return portfolio


async def execute_system_sector_rebalance(
    week_start_date: str,
    week_end_date: str,
    predictions: list[dict],
    price_map: dict[str, dict[str, float]],
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    owner_id: str = SYS_SECTOR_LS_OWNER_ID,
) -> dict[str, Any]:
    """Execute rebalance for a sector long/short portfolio (50% long, 50% short)."""
    if week_start_date < SYS_SECTOR_START_DATE:
        logger.info(
            f"Skipping sector rebalance for window starting {week_start_date} (before portfolio start date {SYS_SECTOR_START_DATE})"
        )
        return {
            "status": "skipped",
            "reason": f"Window start date {week_start_date} is before portfolio start date {SYS_SECTOR_START_DATE}",
        }

    long_sectors, short_sectors = resolve_sector_predictions(predictions)

    if not long_sectors and not short_sectors:
        logger.warning(f"No clean sectors available for rebalancing {owner_id}.")
        return {"status": "skipped", "reason": "No valid sectors"}

    portfolio = await get_or_create_system_portfolio(owner_id)
    current_cash = portfolio.cash_balance
    slip_factor = slippage_bps / 10000.0

    client = get_supabase_client()

    # Idempotency guard: clean up existing trades for this window and revert PnL
    start_ts = f"{week_start_date}T13:30:00Z"
    end_ts = f"{week_end_date}T20:00:00Z"
    existing_trades_res = (
        client.table("trades")
        .select("id, realized_pnl")
        .eq("portfolio_id", str(portfolio.id))
        .in_("executed_at", [start_ts, end_ts])
        .execute()
    )
    existing_trades = existing_trades_res.data or []
    if existing_trades:
        prev_pnl = sum(float(t["realized_pnl"]) for t in existing_trades if t.get("realized_pnl") is not None)
        current_cash = max(0.0, current_cash - prev_pnl)
        for t in existing_trades:
            client.table("trades").delete().eq("id", t["id"]).execute()
        logger.info(
            f"Idempotency cleanup: Removed {len(existing_trades)} existing trades for {owner_id} ({week_start_date} to {week_end_date}), reverted PnL: ${prev_pnl:,.2f}"
        )

    long_budget = (current_cash * 0.5) if (long_sectors and short_sectors) else (current_cash if long_sectors else 0.0)
    short_budget = (
        (current_cash * 0.5) if (long_sectors and short_sectors) else (current_cash if short_sectors else 0.0)
    )

    per_long_alloc = (long_budget / len(long_sectors)) if long_sectors else 0.0
    per_short_alloc = (short_budget / len(short_sectors)) if short_sectors else 0.0

    executed_trades = []
    total_realized_pnl = 0.0

    # 1. Execute Long Legs
    for ticker in long_sectors:
        p_data = price_map.get(ticker)
        if not p_data or not p_data.get("start_price") or not p_data.get("end_price"):
            continue
        entry_p = p_data["start_price"] * (1.0 + slip_factor)
        exit_p = p_data["end_price"] * (1.0 - slip_factor)
        shares = int(per_long_alloc // entry_p) if entry_p > 0 else 0
        if shares <= 0:
            continue
        pnl = (exit_p - entry_p) * shares
        pnl_pct = ((exit_p / entry_p) - 1.0) * 100.0
        total_realized_pnl += pnl

        # Log entry trade
        entry_trade = {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": "BUY",
            "quantity": shares,
            "price": entry_p,
            "total_cost": shares * entry_p,
            "realized_pnl": 0.0,
            "realized_pnl_pct": 0.0,
            "executed_at": f"{week_start_date}T13:30:00Z",
        }
        client.table("trades").insert(entry_trade).execute()

        # Log exit trade with realized PnL
        exit_trade = {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": "SELL",
            "quantity": shares,
            "price": exit_p,
            "total_cost": shares * exit_p,
            "realized_pnl": pnl,
            "realized_pnl_pct": pnl_pct,
            "executed_at": f"{week_end_date}T20:00:00Z",
        }
        client.table("trades").insert(exit_trade).execute()
        executed_trades.append({"ticker": ticker, "side": "LONG", "pnl": pnl, "pnl_pct": pnl_pct})

    # 2. Execute Short Legs
    for ticker in short_sectors:
        p_data = price_map.get(ticker)
        if not p_data or not p_data.get("start_price") or not p_data.get("end_price"):
            continue
        entry_p = p_data["start_price"] * (1.0 - slip_factor)
        exit_p = p_data["end_price"] * (1.0 + slip_factor)
        shares = int(per_short_alloc // entry_p) if entry_p > 0 else 0
        if shares <= 0:
            continue
        pnl = (entry_p - exit_p) * shares
        pnl_pct = ((entry_p - exit_p) / entry_p) * 100.0
        total_realized_pnl += pnl

        # Log entry trade
        entry_trade = {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": "SHORT",
            "quantity": shares,
            "price": entry_p,
            "total_cost": shares * entry_p,
            "realized_pnl": 0.0,
            "realized_pnl_pct": 0.0,
            "executed_at": f"{week_start_date}T13:30:00Z",
        }
        client.table("trades").insert(entry_trade).execute()

        # Log exit trade with realized PnL
        exit_trade = {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": "COVER",
            "quantity": shares,
            "price": exit_p,
            "total_cost": shares * exit_p,
            "realized_pnl": pnl,
            "realized_pnl_pct": pnl_pct,
            "executed_at": f"{week_end_date}T20:00:00Z",
        }
        client.table("trades").insert(exit_trade).execute()
        executed_trades.append({"ticker": ticker, "side": "SHORT", "pnl": pnl, "pnl_pct": pnl_pct})

    # Update portfolio balance and performance
    new_cash = max(0.0, current_cash + total_realized_pnl)
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
            "date": week_end_date,
            "total_equity": new_cash,
            "cash_balance": new_cash,
            "buying_power": new_cash * 4,
            "sma": 0.0,
            "realized": new_cash,
        },
        on_conflict="portfolio_id,date",
    ).execute()

    logger.info(
        f"System Sector L/S Rebalance complete for {owner_id} ({week_end_date}): PnL: ${total_realized_pnl:,.2f}, New Equity: ${new_cash:,.2f}"
    )

    return {
        "status": "success",
        "long_sectors": long_sectors,
        "short_sectors": short_sectors,
        "total_realized_pnl": total_realized_pnl,
        "new_equity": new_cash,
        "trades": executed_trades,
    }


async def execute_mechanical_sector_rebalance(
    owner_id: str,
    sectors: list[str],
    week_start_date: str,
    week_end_date: str,
    price_map: dict[str, dict[str, float]],
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Execute weekly rebalance for a mechanical long-only sector portfolio (e.g. 50% / 50% pair)."""
    if week_start_date < SYS_SECTOR_START_DATE:
        logger.info(
            f"Skipping mechanical rebalance for {owner_id} window {week_start_date} (before {SYS_SECTOR_START_DATE})"
        )
        return {
            "status": "skipped",
            "reason": f"Window start date {week_start_date} is before portfolio start date {SYS_SECTOR_START_DATE}",
        }

    clean_sectors = [s.upper() for s in sectors if s]
    if not clean_sectors:
        logger.warning(f"No sectors provided for mechanical rebalance of {owner_id}.")
        return {"status": "skipped", "reason": "No valid sectors"}

    portfolio = await get_or_create_system_portfolio(owner_id)
    current_cash = portfolio.cash_balance
    slip_factor = slippage_bps / 10000.0

    client = get_supabase_client()

    # Idempotency guard: clean up existing trades for this window and revert PnL
    start_ts = f"{week_start_date}T13:30:00Z"
    end_ts = f"{week_end_date}T20:00:00Z"
    existing_trades_res = (
        client.table("trades")
        .select("id, realized_pnl")
        .eq("portfolio_id", str(portfolio.id))
        .in_("executed_at", [start_ts, end_ts])
        .execute()
    )
    existing_trades = existing_trades_res.data or []
    if existing_trades:
        prev_pnl = sum(float(t["realized_pnl"]) for t in existing_trades if t.get("realized_pnl") is not None)
        current_cash = max(0.0, current_cash - prev_pnl)
        for t in existing_trades:
            client.table("trades").delete().eq("id", t["id"]).execute()
        logger.info(
            f"Idempotency cleanup: Removed {len(existing_trades)} existing trades for {owner_id} ({week_start_date} to {week_end_date}), reverted PnL: ${prev_pnl:,.2f}"
        )

    budget_per_sector = current_cash / len(clean_sectors)
    executed_trades = []
    total_realized_pnl = 0.0

    for ticker in clean_sectors:
        p_data = price_map.get(ticker)
        if not p_data or not p_data.get("start_price") or not p_data.get("end_price"):
            continue

        entry_p = p_data["start_price"] * (1.0 + slip_factor)
        exit_p = p_data["end_price"] * (1.0 - slip_factor)
        shares = int(budget_per_sector // entry_p) if entry_p > 0 else 0
        if shares <= 0:
            continue

        pnl = (exit_p - entry_p) * shares
        pnl_pct = ((exit_p / entry_p) - 1.0) * 100.0
        total_realized_pnl += pnl

        # Log entry trade
        entry_trade = {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": "BUY",
            "quantity": shares,
            "price": entry_p,
            "total_cost": shares * entry_p,
            "realized_pnl": 0.0,
            "realized_pnl_pct": 0.0,
            "executed_at": f"{week_start_date}T13:30:00Z",
        }
        client.table("trades").insert(entry_trade).execute()

        # Log exit trade
        exit_trade = {
            "portfolio_id": str(portfolio.id),
            "ticker": ticker,
            "signal": "SELL",
            "quantity": shares,
            "price": exit_p,
            "total_cost": shares * exit_p,
            "realized_pnl": pnl,
            "realized_pnl_pct": pnl_pct,
            "executed_at": f"{week_end_date}T20:00:00Z",
        }
        client.table("trades").insert(exit_trade).execute()
        executed_trades.append({"ticker": ticker, "pnl": pnl, "pnl_pct": pnl_pct})

    new_cash = max(0.0, current_cash + total_realized_pnl)
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
            "date": week_end_date,
            "total_equity": new_cash,
            "cash_balance": new_cash,
            "buying_power": new_cash * 4,
            "sma": 0.0,
            "realized": new_cash,
        },
        on_conflict="portfolio_id,date",
    ).execute()

    logger.info(
        f"Mechanical Rebalance complete for {owner_id} ({week_end_date}): "
        f"Sectors: {clean_sectors}, PnL: ${total_realized_pnl:,.2f}, New Equity: ${new_cash:,.2f}"
    )

    return {
        "status": "success",
        "owner_id": owner_id,
        "sectors": clean_sectors,
        "total_realized_pnl": total_realized_pnl,
        "new_equity": new_cash,
        "trades": executed_trades,
    }


async def execute_all_system_mechanical_sector_rebalances(
    week_start_date: str,
    week_end_date: str,
    price_map: dict[str, dict[str, float]],
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> list[dict[str, Any]]:
    """Resolve and execute all 4 mechanical sector portfolios for an evaluated window."""
    if week_start_date < SYS_SECTOR_START_DATE:
        return []

    client = get_supabase_client()
    # 1. Fetch closest correlation run on or before week_start_date
    run_res = (
        client.table("correlation_runs")
        .select("id, tickers")
        .lte("run_date", week_start_date)
        .order("run_date", desc=True)
        .limit(1)
        .execute()
    )
    if not run_res.data:
        logger.warning(f"No correlation run found on or before {week_start_date} for mechanical rebalance.")
        return []

    run_id = run_res.data[0]["id"]
    ref_tickers = run_res.data[0].get("tickers") or list(price_map.keys())
    universe = [t for t in MECHANICAL_SECTOR_UNIVERSE if t in ref_tickers] or MECHANICAL_SECTOR_UNIVERSE

    # 2. Fetch correlation_data for this run
    data_res = (
        client.table("correlation_data")
        .select("ticker_a, ticker_b, pearson_corr, returns_a_7d, returns_b_7d, returns_a_30d, returns_b_30d")
        .eq("run_id", run_id)
        .execute()
    )
    if not data_res.data:
        logger.warning(f"No correlation data found for run {run_id} on {week_start_date}.")
        return []

    # 3. Resolve target sectors
    resolved = resolve_mechanical_sectors(data_res.data, universe)

    results = []
    for owner_id, sectors in resolved.items():
        try:
            res = await execute_mechanical_sector_rebalance(
                owner_id=owner_id,
                sectors=sectors,
                week_start_date=week_start_date,
                week_end_date=week_end_date,
                price_map=price_map,
                slippage_bps=slippage_bps,
            )
            results.append(res)
        except Exception as e:
            logger.exception(f"Failed to execute mechanical rebalance for {owner_id}: {e}")

    return results
