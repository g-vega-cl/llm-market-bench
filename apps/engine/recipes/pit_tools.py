"""Strict point-in-time (PIT) tool router preventing lookahead bias during backtests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from core.config import logger
from core.db import get_supabase_client
from recipes.intraday_bars import fetch_intraday_bars_for_ticker, resolve_slot_price
from tools._compat import MarketDataManager
from tools.market_data import compute_volume_context
from tools.technicals import execute_technical_indicators_tool
from tools.valuation import _format_key_metric_period


def _resolve_as_of(cutoff_date: str | None, as_of_utc: str | None) -> tuple[str, str, datetime]:
    if as_of_utc:
        dt = datetime.fromisoformat(str(as_of_utc).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt_utc = dt.astimezone(UTC)
        return dt_utc.date().isoformat(), dt_utc.isoformat(), dt_utc
    day = str(cutoff_date or datetime.now(UTC).date().isoformat())[:10]
    dt_utc = datetime.fromisoformat(f"{day}T21:00:00+00:00")
    return day, dt_utc.isoformat(), dt_utc


def _fetch_pit_daily_rows(sb: Any, ticker: str, cutoff_day: str, limit: int) -> list[dict[str, Any]]:
    """Fetch completed daily bars STRICTLY before cutoff_day to prevent same-day EOD leakage."""
    res = (
        sb.table("price_history")
        .select("price, close, volume, fetched_at")
        .eq("ticker", ticker)
        .lt("fetched_at", f"{cutoff_day}T00:00:00+00:00")
        .order("fetched_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows: list[dict[str, Any]] = []
    for row in res.data or []:
        px = row.get("close") if row.get("close") is not None else row.get("price")
        if px is None:
            continue
        rows.append(
            {
                "price": float(px),
                "volume": int(row["volume"]) if row.get("volume") is not None else None,
                "fetched_at": str(row.get("fetched_at", "")),
            }
        )
    return rows


async def _pit_stock_quote(ticker: str, cutoff_day: str, as_of_iso: str, as_of_dt: datetime) -> str:
    sb = get_supabase_client()
    start_day = (as_of_dt - timedelta(days=3)).date().isoformat()
    res = (
        sb.table("recipe_intraday_bars")
        .select("ticker, bar_time_utc, open, high, low, close, volume")
        .eq("ticker", ticker)
        .gte("bar_time_utc", f"{start_day}T00:00:00+00:00")
        .lte("bar_time_utc", as_of_iso)
        .order("bar_time_utc", desc=False)
        .limit(200)
        .execute()
    )
    bars = list(res.data or [])
    if not bars:
        bars = [
            b
            for b in await fetch_intraday_bars_for_ticker(sb, ticker, start_day, cutoff_day)
            if str(b.get("bar_time_utc", "")) <= as_of_iso
        ]
    daily_rows = _fetch_pit_daily_rows(sb, ticker, cutoff_day, 5)
    daily_map = {ticker: {str(r["fetched_at"])[:10]: r["price"] for r in daily_rows}}
    px = resolve_slot_price(bars, daily_map, ticker, as_of_dt)
    if px is None:
        return f"No point-in-time quote available for {ticker} at {as_of_iso}."
    return f"Ticker: {ticker}\nPoint-in-Time Price: ${px:.2f}\nSimulated Timestamp: {as_of_iso}\nStatus: VALID"


def _pit_price_history(ticker: str, cutoff_day: str, days: int) -> str:
    sb = get_supabase_client()
    rows = _fetch_pit_daily_rows(sb, ticker, cutoff_day, max(1, int(days)))
    if not rows:
        return f"No historical price data found for {ticker} up to {cutoff_day}."
    lines = [f"Historical Price Data for {ticker} up to {cutoff_day} (Recent first):"]
    for entry in rows:
        vol_str = f", Volume: {entry['volume']}" if entry.get("volume") is not None else ""
        lines.append(f"- {entry['fetched_at']}: ${entry['price']:.2f}{vol_str}")
    lines.append(f"\nVolume Context: {compute_volume_context(rows)}")
    return "\n".join(lines)


def _pit_ticker_news(ticker: str, as_of_iso: str, limit: int) -> str:
    sb = get_supabase_client()
    res = (
        sb.table("recipe_news_corpus")
        .select("article_id, title, date_published, tickers, full_text")
        .contains("tickers", [ticker])
        .lte("date_published", as_of_iso)
        .order("date_published", desc=True)
        .limit(max(1, int(limit)))
        .execute()
    )
    rows = res.data or []
    if not rows:
        return f"No point-in-time news found for {ticker} up to {as_of_iso}."
    parts = [f"Point-in-Time News for {ticker} (<= {as_of_iso[:16]}):"]
    for row in rows:
        excerpt = str(row.get("full_text") or "")[:320].strip()
        parts.append(f"- [{str(row.get('date_published', ''))[:16]}] {row.get('title', '')}\n  {excerpt}")
    return "\n".join(parts)


def _pit_todays_news_menu(as_of_iso: str, as_of_dt: datetime) -> str:
    sb = get_supabase_client()
    floor_iso = (as_of_dt - timedelta(hours=48)).isoformat()
    res = (
        sb.table("recipe_news_corpus")
        .select("article_id, title, date_published, tickers")
        .gte("date_published", floor_iso)
        .lte("date_published", as_of_iso)
        .order("date_published", desc=True)
        .limit(15)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return f"No point-in-time news headlines available in the 48h window up to {as_of_iso[:16]}."
    lines = [f"=== POINT-IN-TIME NEWS MENU (<= {as_of_iso[:16]}) ==="]
    for row in rows:
        tkrs = ", ".join(row.get("tickers") or []) or "MARKET"
        lines.append(
            f"- Source ID: {row.get('article_id')} | [{str(row.get('date_published', ''))[:16]}] {row.get('title', '')} ({tkrs})"
        )
    return "\n".join(lines)


def _pit_fetch_newsletter(source_ids: list[str], as_of_iso: str) -> str:
    if not source_ids:
        return "No source IDs specified."
    sb = get_supabase_client()
    res_nl = (
        sb.table("newsletter_snapshots")
        .select("source_id, content, sender, subject, date")
        .in_("source_id", source_ids)
        .lte("date", as_of_iso)
        .execute()
    )
    rows = res_nl.data or []
    parts = [
        f"Source ID: {r.get('source_id')} | Date: {r.get('date')} | Subject: {r.get('subject')}\n{r.get('content', '')}"
        for r in rows
    ]
    matched_ids = {str(r.get("source_id", "")) for r in rows}
    remaining = [sid for sid in source_ids if sid not in matched_ids]
    if remaining:
        res_corpus = (
            sb.table("recipe_news_corpus")
            .select("article_id, title, date_published, full_text")
            .in_("article_id", remaining)
            .lte("date_published", as_of_iso)
            .execute()
        )
        for r in res_corpus.data or []:
            parts.append(
                f"Source ID: {r.get('article_id')} | Date: {r.get('date_published')} | "
                f"Title: {r.get('title')}\n{r.get('full_text', '')}"
            )
    if not parts:
        return f"No point-in-time newsletters found matching IDs up to {as_of_iso[:16]}."
    return "\n\n".join(parts)


def _pit_search_memories(query: str, as_of_iso: str, limit: int) -> str:
    if not query.strip():
        return "No query specified."
    sb = get_supabase_client()
    first_term = next((w.strip() for w in query.split() if len(w.strip()) >= 3), query.strip())
    res = (
        sb.table("memories")
        .select("id, content, created_at, memory_type, importance_score")
        .lte("created_at", as_of_iso)
        .ilike("content", f"%{first_term}%")
        .order("created_at", desc=True)
        .limit(max(1, int(limit)))
        .execute()
    )
    rows = res.data or []
    if not rows:
        return f"No point-in-time memories found matching '{query}' up to {as_of_iso[:16]}."
    return "\n".join(
        f"- [{str(r.get('created_at', ''))[:16]} | {r.get('memory_type', 'EVENT')} | imp={r.get('importance_score', 5)}] {r.get('content', '')}"
        for r in rows
    )


def _pit_market_feeling(as_of_iso: str) -> str:
    sb = get_supabase_client()
    res = (
        sb.table("market_feeling")
        .select(
            "sentiment_label, market_direction, confidence_score, why_explanation, primary_concern, secondary_concern, created_at"
        )
        .lte("created_at", as_of_iso)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return f"No market feeling snapshot available up to {as_of_iso[:16]}."
    f = rows[0]
    concerns = [c for c in (f.get("primary_concern"), f.get("secondary_concern")) if c]
    concern_line = f"\nConcerns: {' | '.join(concerns)}" if concerns else ""
    return (
        f"=== POINT-IN-TIME MARKET FEELING (<= {as_of_iso[:16]}) ===\n"
        f"Sentiment: {f.get('sentiment_label', 'Neutral')} | Direction: {f.get('market_direction', 'N/A')} | "
        f"Confidence: {f.get('confidence_score', 'N/A')}%\n"
        f"Rationale: {f.get('why_explanation') or ''}{concern_line}"
    )


async def _pit_earnings_history(ticker: str, cutoff_day: str, limit: int) -> str:
    manager = MarketDataManager()
    data = await manager.get_earnings_history(ticker, max(limit, 24))
    past = [e for e in (data or []) if str(e.get("date", ""))[:10] <= cutoff_day and not e.get("isUpcoming")]
    past = past[:limit]
    if not past:
        return f"No historical earnings reports found for {ticker} on or before {cutoff_day}."
    lines = [f"Historical Earnings Reports for {ticker.upper()} (on or before {cutoff_day}):"]
    for entry in past:
        act_eps = f"${entry['epsActual']:.2f}" if entry.get("epsActual") is not None else "N/A"
        est_eps = f"${entry['epsEstimated']:.2f}" if entry.get("epsEstimated") is not None else "N/A"
        lines.append(f"- Date: {entry['date']} | EPS Actual {act_eps} vs Est {est_eps}")
    return "\n".join(lines)


async def _pit_key_metrics(ticker: str, cutoff_day: str, period: str, limit: int) -> str:
    manager = MarketDataManager()
    data = await manager.get_key_metrics(ticker, period, max(limit, 8))
    filtered = [entry for entry in (data or []) if str(entry.get("date", ""))[:10] <= cutoff_day][:limit]
    if not filtered:
        return f"No fundamental key metrics found for {ticker} on or before {cutoff_day}."
    chunks = [f"Fundamental Key Metrics for {ticker.upper()} ({period.capitalize()}, <= {cutoff_day}):"]
    for i, entry in enumerate(filtered, 1):
        chunks.append(_format_key_metric_period(i, entry))
    return "".join(chunks)


async def _pit_technicals(ticker: str, args: dict[str, Any], as_of_dt: datetime) -> str:
    # Restrict technicals to strictly prior completed daily closes to prevent same-day EOD leakage.
    prior_day = (as_of_dt - timedelta(days=1)).date().isoformat()
    return await execute_technical_indicators_tool(
        ticker=ticker or args.get("ticker", "SPY"),
        cutoff_date=prior_day,
        strict_pit=True,
    )


PIT_SAFE_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "get_stock_quote",
        "get_price_history",
        "get_technical_indicators",
        "get_ticker_news",
        "get_todays_news_menu",
        "fetch_newsletter_content",
        "search_past_memories",
        "get_market_feeling",
        "get_earnings_history",
        "get_key_metrics",
    }
)


def _build_pit_dispatch(
    ticker: str,
    args: dict[str, Any],
    cutoff_day: str,
    as_of_iso: str,
    as_of_dt: datetime,
) -> dict[str, Any]:
    return {
        "get_stock_quote": lambda: _pit_stock_quote(ticker, cutoff_day, as_of_iso, as_of_dt),
        "get_price_history": lambda: _pit_price_history(ticker, cutoff_day, int(args.get("days", 7))),
        "get_technical_indicators": lambda: _pit_technicals(ticker, args, as_of_dt),
        "get_ticker_news": lambda: _pit_ticker_news(ticker, as_of_iso, int(args.get("limit", 5))),
        "get_todays_news_menu": lambda: _pit_todays_news_menu(as_of_iso, as_of_dt),
        "fetch_newsletter_content": lambda: _pit_fetch_newsletter(list(args.get("source_ids") or []), as_of_iso),
        "search_past_memories": lambda: _pit_search_memories(
            str(args.get("query", "")), as_of_iso, int(args.get("limit", 5))
        ),
        "get_market_feeling": lambda: _pit_market_feeling(as_of_iso),
        "get_earnings_history": lambda: _pit_earnings_history(ticker, cutoff_day, int(args.get("limit", 8))),
        "get_key_metrics": lambda: _pit_key_metrics(
            ticker, cutoff_day, str(args.get("period", "annual")), int(args.get("limit", 2))
        ),
    }


async def execute_pit_tool(
    name: str,
    ticker: str,
    args: dict[str, Any],
    *,
    cutoff_date: str | None = None,
    as_of_utc: str | None = None,
) -> str:
    """Execute PIT-safe tool variant or fail closed when live-only lookahead would occur."""
    cutoff_day, as_of_iso, as_of_dt = _resolve_as_of(cutoff_date, as_of_utc)
    handlers = _build_pit_dispatch(ticker, args, cutoff_day, as_of_iso, as_of_dt)
    handler = handlers.get(name)
    if handler is None:
        return f"Tool '{name}' is disabled in point-in-time backtests (cutoff {cutoff_day}) to prevent lookahead bias."
    try:
        res = handler()
        if hasattr(res, "__await__"):
            return await res
        return str(res)
    except Exception as exc:
        logger.exception("Error in point-in-time tool %s for %s", name, ticker)
        return f"Error executing point-in-time {name}: {exc}"
