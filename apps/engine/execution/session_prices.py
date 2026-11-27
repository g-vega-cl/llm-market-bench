"""Session-scoped entry prices for live and backfilled trades.

A trade stamped with session T must be priced from T's bar. A backfill that runs
on day T+N must never inherit the quote from the day it happens to execute.
"""

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from core.config import logger
from core.db import get_supabase_client

QuoteFetcher = Callable[[list[str]], Awaitable[dict[str, Any]]]


def quote_price(quote: Any) -> float | None:
    """Prefer the session open from a live quote, then fall back to its price."""
    open_price = getattr(quote, "open_price", None)
    raw = open_price if open_price and float(open_price) > 0 else getattr(quote, "price", None)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


async def _live_quotes(tickers: list[str]) -> dict[str, Any]:
    from execution.market_data import MarketDataManager

    return await MarketDataManager().get_quotes(tickers, force_refresh=True)


async def historical_open_prices(tickers: list[str], session_date: str, client: Any = None) -> dict[str, float]:
    """Read session bars from price_history, keyed by the audit's fetched_at date."""
    if not tickers:
        return {}
    sb = client or get_supabase_client()
    session_date = session_date[:10]
    rows = (
        sb.table("price_history")
        .select("ticker,open,price,fetched_at")
        .in_("ticker", [t.upper() for t in tickers])
        .gte("fetched_at", f"{session_date}T00:00:00Z")
        .lte("fetched_at", f"{session_date}T23:59:59Z")
        .order("fetched_at", desc=False)
        .limit(1000)
        .execute()
        .data
        or []
    )
    prices: dict[str, float] = {}
    for row in rows:
        ticker = str(row.get("ticker", "")).upper()
        if ticker in prices:
            continue
        raw = row.get("open")
        if raw is None:
            raw = row.get("price")
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value > 0:
            prices[ticker] = value
    return prices


async def resolve_entry_prices(
    tickers: list[str],
    session_date: str,
    *,
    client: Any = None,
    quote_fetcher: QuoteFetcher | None = None,
    today: str | None = None,
) -> tuple[dict[str, float], list[str]]:
    """Return prices for a session plus the tickers that have no trustworthy price.

    Today uses the live quote path. Any other date reads that session's bar and
    omits missing tickers so callers skip the leg instead of using a live price.
    """
    wanted = sorted({str(t).upper() for t in tickers if t})
    session_date = session_date[:10]
    today = (today or date.today().isoformat())[:10]

    if session_date == today:
        quotes = await (quote_fetcher or _live_quotes)(wanted)
        prices: dict[str, float] = {}
        for ticker in wanted:
            quote = quotes.get(ticker)
            value = quote_price(quote) if quote is not None else None
            if value is not None:
                prices[ticker] = value
    else:
        prices = await historical_open_prices(wanted, session_date, client=client)

    missing = [ticker for ticker in wanted if ticker not in prices]
    if missing:
        logger.warning(f"No {session_date} session bar for {', '.join(missing)}; skipping those legs")
    return prices, missing
