"""Evaluation task for Daily Stock Picker Arena (3 Up, 3 Down).

Runs post-market close (16:05+ ET) to fetch RTH Open and Close prices,
calculate directional hit rates, Long/Short spread alpha, and benchmark SPY comparison,
and updates status in daily_stock_baskets and daily_stock_picks tables.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from core.config import logger
from core.conviction_scoring import conviction_points
from core.db import get_supabase_client
from tasks.evaluate_daily_predictions import fetch_intraday_prices

PriceTuple = tuple[float | None, float | None, float | None, float | None]


def get_ny_now() -> datetime:
    """Return current datetime in America/New_York timezone."""
    return datetime.now(ZoneInfo("America/New_York"))


async def _fetch_session_prices(
    tickers: set[str],
    session_date: str,
    force_recalc: bool,
) -> dict[str, PriceTuple]:
    """Fetch RTH OHLC prices for unique session tickers under a concurrency cap."""
    price_map: dict[str, PriceTuple] = {}
    semaphore = asyncio.Semaphore(5)

    async def _fetch(ticker: str) -> None:
        async with semaphore:
            try:
                price_map[ticker] = await fetch_intraday_prices(ticker, session_date, force_refresh=force_recalc)
            except Exception:
                logger.exception(f"Error fetching prices for {ticker} on {session_date}")
                price_map[ticker] = (None, None, None, None)

    await asyncio.gather(*[_fetch(t) for t in tickers])
    return price_map


def _grade_pick(
    pick: dict[str, Any],
    prices: PriceTuple,
    session_date: str,
    evaluated_at_iso: str,
) -> dict[str, Any]:
    """Grade one pick against RTH open/close prices while preserving all NOT NULL columns."""
    ticker = pick["ticker"]
    direction = str(pick["direction"]).upper()
    confidence = float(pick.get("confidence", 60.0))
    open_price, _, _, close_price = prices

    # Financial sanity guard: check rounded open_price too so chk_pick_evaluation_invariants (open_price > 0) holds.
    if open_price is None or close_price is None or open_price <= 0 or round(open_price, 2) <= 0:
        logger.warning(
            f"Invalid price data for {ticker} on {session_date} (open={open_price}, close={close_price}). Marking cancelled."
        )
        return {
            **pick,
            "status": "cancelled",
            "open_price": None,
            "close_price": None,
            "stock_return_pct": None,
            "position_return_pct": None,
            "is_hit": None,
            "conviction_points": None,
            "evaluated_at": None,
        }

    stock_return = round(((close_price - open_price) / open_price) * 100.0, 4)
    pos_return = stock_return if direction == "UP" else -stock_return
    is_hit = (close_price > open_price) if direction == "UP" else (close_price < open_price)

    return {
        **pick,
        "status": "evaluated",
        "open_price": round(open_price, 2),
        "close_price": round(close_price, 2),
        "stock_return_pct": stock_return,
        "position_return_pct": pos_return,
        "is_hit": is_hit,
        "conviction_points": conviction_points(confidence, is_hit),
        "evaluated_at": evaluated_at_iso,
    }


def _aggregate_basket(
    basket: dict[str, Any],
    basket_picks: list[dict[str, Any]],
    spy_return_pct: float | None,
    evaluated_at_iso: str,
) -> dict[str, Any]:
    """Compute basket-level L/S alpha and hit rate while preserving all NOT NULL columns."""
    valid_picks = [p for p in basket_picks if p["status"] == "evaluated"]
    if not valid_picks:
        logger.warning(f"Basket {basket['id']} ({basket['model_name']}) has zero valid evaluated picks.")
        return {
            **basket,
            "status": "cancelled",
            "directional_hit_rate": None,
            "mean_long_return_pct": None,
            "mean_short_return_pct": None,
            "ls_spread_alpha_pct": None,
            "excess_alpha_vs_spy_pct": None,
            "benchmark_spy_return_pct": spy_return_pct,
            "evaluated_at": evaluated_at_iso,
        }

    long_returns = [p["position_return_pct"] for p in valid_picks if str(p["direction"]).upper() == "UP"]
    short_stock_returns = [p["stock_return_pct"] for p in valid_picks if str(p["direction"]).upper() == "DOWN"]

    mean_long = round(sum(long_returns) / len(long_returns), 4) if long_returns else 0.0
    mean_short = round(sum(short_stock_returns) / len(short_stock_returns), 4) if short_stock_returns else 0.0
    ls_alpha = round(mean_long - mean_short, 4)
    excess_alpha = round(ls_alpha - spy_return_pct, 4) if spy_return_pct is not None else None
    hits = sum(1 for p in valid_picks if p["is_hit"])

    return {
        **basket,
        "status": "evaluated",
        "directional_hit_rate": round((hits / len(valid_picks)) * 100.0, 2),
        "mean_long_return_pct": mean_long,
        "mean_short_return_pct": mean_short,
        "ls_spread_alpha_pct": ls_alpha,
        "excess_alpha_vs_spy_pct": excess_alpha,
        "benchmark_spy_return_pct": spy_return_pct,
        "evaluated_at": evaluated_at_iso,
    }


async def evaluate_stock_picks(
    target_date: str | None = None,
    force_recalc: bool = False,
) -> dict[str, Any]:
    """Evaluate pending daily stock baskets and picks for target_date.

    Args:
        target_date: ISO date string (YYYY-MM-DD). Defaults to today's NY date.
        force_recalc: If True, re-evaluates already evaluated records.
    """
    now_et = get_ny_now()
    session_date = target_date or now_et.strftime("%Y-%m-%d")

    # Safety: skip evaluating today's session if market is still open (prior to 16:05 ET)
    if session_date == now_et.strftime("%Y-%m-%d"):
        ny_minutes = now_et.hour * 60 + now_et.minute
        if ny_minutes < 965 and not force_recalc:  # 16:05 ET = 965 minutes
            logger.info(
                f"Market still active for {session_date} ({now_et.strftime('%H:%M')} ET < 16:05). Skipping evaluation."
            )
            return {"status": "market_active", "target_date": session_date}

    supabase = get_supabase_client()
    basket_query = supabase.table("daily_stock_baskets").select("*").eq("target_date", session_date)
    if not force_recalc:
        basket_query = basket_query.eq("status", "pending")

    baskets = basket_query.execute().data or []
    if not baskets:
        logger.info(f"No stock baskets to evaluate for {session_date} (force={force_recalc}).")
        return {"status": "no_baskets", "target_date": session_date}

    basket_ids = [b["id"] for b in baskets]
    picks = supabase.table("daily_stock_picks").select("*").in_("basket_id", basket_ids).execute().data or []

    unique_tickers = {p["ticker"] for p in picks} | {"SPY"}
    logger.info(f"Fetching RTH price data for {len(unique_tickers)} tickers on {session_date}...")
    price_map = await _fetch_session_prices(unique_tickers, session_date, force_recalc)

    spy_open, _, _, spy_close = price_map.get("SPY", (None, None, None, None))
    spy_return_pct = (
        round(((spy_close - spy_open) / spy_open) * 100.0, 4)
        if spy_open is not None and spy_close is not None and spy_open > 0
        else None
    )

    evaluated_at_iso = datetime.now(UTC).isoformat()
    evaluated_picks: list[dict[str, Any]] = []
    picks_by_basket: dict[str, list[dict[str, Any]]] = {}

    for pick in picks:
        graded = _grade_pick(
            pick,
            price_map.get(pick["ticker"], (None, None, None, None)),
            session_date,
            evaluated_at_iso,
        )
        evaluated_picks.append(graded)
        picks_by_basket.setdefault(pick["basket_id"], []).append(graded)

    if evaluated_picks:
        supabase.table("daily_stock_picks").upsert(evaluated_picks, on_conflict="id").execute()

    evaluated_baskets = [
        _aggregate_basket(basket, picks_by_basket.get(basket["id"], []), spy_return_pct, evaluated_at_iso)
        for basket in baskets
    ]

    if evaluated_baskets:
        supabase.table("daily_stock_baskets").upsert(evaluated_baskets, on_conflict="id").execute()

    logger.info(
        f"Evaluation complete for {session_date}. Evaluated {len(evaluated_baskets)} baskets and {len(evaluated_picks)} picks."
    )
    return {
        "status": "success",
        "target_date": session_date,
        "baskets_evaluated": len(evaluated_baskets),
        "picks_evaluated": len(evaluated_picks),
        "spy_return_pct": spy_return_pct,
    }
