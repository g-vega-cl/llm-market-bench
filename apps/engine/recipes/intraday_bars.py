"""Point-in-time 3x/day ET slot expansion and multi-source intraday bar caching."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from core.config import ALPACA_API_KEY, ALPACA_SECRET_KEY, logger
from core.time_utils import EASTERN_TZ

TRADING_SLOTS_ET: tuple[tuple[int, int], ...] = ((9, 30), (12, 30), (15, 30))
CORPUS_MIN_DATE = "2026-02-09"
_EXACT_MATCH_TOLERANCE_SECONDS = 300
_PRIOR_BAR_MAX_AGE_SECONDS = 7200


def expand_dates_to_et_slots(dates: list[str]) -> list[dict[str, Any]]:
    """Expand sorted YYYY-MM-DD dates into ordered 09:30 / 12:30 / 15:30 ET slots."""
    slots: list[dict[str, Any]] = []
    for day_str in dates:
        year, month, day = (int(part) for part in day_str[:10].split("-"))
        for hour_et, minute_et in TRADING_SLOTS_ET:
            dt_et = datetime(year, month, day, hour_et, minute_et, tzinfo=EASTERN_TZ)
            dt_utc = dt_et.astimezone(UTC)
            slots.append(
                {
                    "slot_label": f"{day_str[:10]} {hour_et:02d}:{minute_et:02d} ET",
                    "day_str": day_str[:10],
                    "hour_et": hour_et,
                    "minute_et": minute_et,
                    "timestamp_utc": dt_utc,
                    "timestamp_iso": dt_utc.isoformat(),
                }
            )
    return slots


def _parse_bar_dt_utc(raw_ts: Any) -> datetime | None:
    if isinstance(raw_ts, datetime):
        return raw_ts.astimezone(UTC) if raw_ts.tzinfo else raw_ts.replace(tzinfo=EASTERN_TZ).astimezone(UTC)
    if not raw_ts:
        return None
    text = str(raw_ts).strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=EASTERN_TZ)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def _normalize_bars(raw_bars: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in raw_bars:
        dt_utc = _parse_bar_dt_utc(row.get("bar_time_utc") or row.get("date") or row.get("timestamp"))
        if dt_utc is None:
            continue
        close_px = row.get("close") if row.get("close") is not None else row.get("price")
        open_px = row.get("open") if row.get("open") is not None else close_px
        if open_px is None and close_px is None:
            continue
        o_val = float(open_px if open_px is not None else close_px)
        c_val = float(close_px if close_px is not None else o_val)
        normalized.append(
            {
                "bar_time_utc": dt_utc.isoformat(),
                "open": round(o_val, 4),
                "high": round(float(row.get("high") if row.get("high") is not None else max(o_val, c_val)), 4),
                "low": round(float(row.get("low") if row.get("low") is not None else min(o_val, c_val)), 4),
                "close": round(c_val, 4),
                "volume": int(float(row.get("volume") or 0)),
                "source": str(row.get("source") or source),
            }
        )
    normalized.sort(key=lambda item: item["bar_time_utc"])
    return normalized


def _has_slot_coverage(bars: list[dict[str, Any]], start_day: str, end_day: str) -> bool:
    """True when Postgres cache holds >=3x/day intraday coverage across >=70% of weekdays."""
    if not bars:
        return False
    covered_days = {str(b.get("bar_time_utc", ""))[:10] for b in bars if b.get("bar_time_utc")}
    start_d = datetime.fromisoformat(start_day[:10]).date()
    end_d = datetime.fromisoformat(end_day[:10]).date()
    weekdays = sum(
        1 for offset in range((end_d - start_d).days + 1) if (start_d + timedelta(days=offset)).weekday() < 5
    )
    required_days = max(1, int(weekdays * 0.7))
    return len(covered_days) >= required_days and len(bars) >= len(covered_days) * 3


async def _fetch_fmp_hourly(ticker: str, start_day: str, end_day: str) -> list[dict[str, Any]]:
    from execution.providers.fmp import FMPProvider

    provider = FMPProvider()
    if not getattr(provider, "api_key", None):
        return []
    return await provider.get_hourly_history(ticker.upper(), start_day, end_day)


async def _fetch_alpaca_hourly(ticker: str, start_day: str, end_day: str) -> list[dict[str, Any]]:
    if not (ALPACA_API_KEY and ALPACA_SECRET_KEY):
        return []
    try:
        from alpaca.data.enums import DataFeed
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        start_dt = datetime.fromisoformat(f"{start_day[:10]}T00:00:00+00:00")
        end_dt = datetime.fromisoformat(f"{end_day[:10]}T23:59:59+00:00") + timedelta(hours=5)
        client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
        req = StockBarsRequest(
            symbol_or_symbols=ticker.upper(),
            timeframe=TimeFrame.Hour,
            start=start_dt,
            end=end_dt,
            feed=DataFeed.IEX,
        )
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, client.get_stock_bars, req)
        raw_bars = resp.data.get(ticker.upper(), []) if hasattr(resp, "data") else []
        out: list[dict[str, Any]] = []
        for bar in raw_bars:
            ts = (
                bar.timestamp.astimezone(UTC).isoformat()
                if hasattr(bar.timestamp, "astimezone")
                else str(bar.timestamp)
            )
            out.append(
                {
                    "bar_time_utc": ts,
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume or 0),
                    "source": "alpaca",
                }
            )
        return out
    except Exception:
        logger.exception("Alpaca historical hourly fetch failed for %s (%s..%s)", ticker, start_day, end_day)
        return []


def upsert_intraday_bars(sb_client: Any, ticker: str, bars: list[dict[str, Any]]) -> None:
    """Persist normalized intraday bars into public.recipe_intraday_bars."""
    if not bars or sb_client is None:
        return
    clean_ticker = ticker.upper().strip()
    payload = [
        {
            "ticker": clean_ticker,
            "bar_time_utc": b["bar_time_utc"],
            "open": b["open"],
            "high": b["high"],
            "low": b["low"],
            "close": b["close"],
            "volume": int(b.get("volume") or 0),
            "source": b.get("source") or "fmp",
        }
        for b in bars
    ]
    try:
        sb_client.table("recipe_intraday_bars").upsert(payload, on_conflict="ticker,bar_time_utc").execute()
    except Exception:
        logger.warning("Failed upserting %d intraday bars for %s", len(payload), clean_ticker, exc_info=True)


async def fetch_intraday_bars_for_ticker(
    sb_client: Any,
    ticker: str,
    start_day: str,
    end_day: str,
) -> list[dict[str, Any]]:
    """Load intraday hourly bars from Postgres cache, falling back to FMP then Alpaca and upserting."""
    clean_ticker = ticker.upper().strip()
    if not clean_ticker:
        return []

    start_iso = f"{start_day[:10]}T00:00:00+00:00"
    end_iso = (datetime.fromisoformat(f"{end_day[:10]}T23:59:59+00:00") + timedelta(hours=5)).isoformat()

    try:
        res = (
            sb_client.table("recipe_intraday_bars")
            .select("ticker, bar_time_utc, open, high, low, close, volume, source")
            .eq("ticker", clean_ticker)
            .gte("bar_time_utc", start_iso)
            .lte("bar_time_utc", end_iso)
            .order("bar_time_utc", desc=False)
            .limit(2000)
            .execute()
        )
        cached = _normalize_bars(res.data or [], source="cache")
        if _has_slot_coverage(cached, start_day, end_day):
            return cached
    except Exception:
        logger.warning("Failed reading recipe_intraday_bars cache for %s", clean_ticker, exc_info=True)

    fmp_raw = await _fetch_fmp_hourly(clean_ticker, start_day[:10], end_day[:10])
    fmp_bars = _normalize_bars(fmp_raw, source="fmp")
    if fmp_bars:
        upsert_intraday_bars(sb_client, clean_ticker, fmp_bars)
        return fmp_bars

    alpaca_raw = await _fetch_alpaca_hourly(clean_ticker, start_day[:10], end_day[:10])
    alpaca_bars = _normalize_bars(alpaca_raw, source="alpaca")
    if alpaca_bars:
        upsert_intraday_bars(sb_client, clean_ticker, alpaca_bars)
        return alpaca_bars

    return []


def resolve_slot_price(
    bars: list[dict[str, Any]],
    daily_closes: dict[str, dict[str, float]],
    ticker: str,
    slot_dt_utc: datetime,
) -> float | None:
    """Resolve zero-lookahead execution price for ticker at exact UTC slot timestamp.

    Uses bar.open when a bar opens within +-5 minutes of slot_dt_utc, else bar.close
    of the most recent bar completed at or before slot_dt_utc (max 2h lookback), else
    daily price_history fallback.
    """
    clean_ticker = ticker.upper().strip()
    exact_match: tuple[float, float] | None = None
    prior_match: tuple[datetime, float] | None = None

    for bar in bars:
        bar_dt = _parse_bar_dt_utc(bar.get("bar_time_utc"))
        if bar_dt is None:
            continue
        diff_sec = (slot_dt_utc - bar_dt).total_seconds()
        # Enforce bar_dt <= slot_dt_utc strictly (never use bars opening after slot_dt_utc).
        if 0 <= diff_sec <= _EXACT_MATCH_TOLERANCE_SECONDS:
            open_px = float(bar.get("open") or bar.get("close") or 0.0)
            if open_px > 0 and (exact_match is None or diff_sec < exact_match[0]):
                exact_match = (diff_sec, open_px)
        elif 0 <= diff_sec <= _PRIOR_BAR_MAX_AGE_SECONDS:
            close_px = float(bar.get("close") or bar.get("open") or 0.0)
            if close_px > 0 and (prior_match is None or bar_dt > prior_match[0]):
                prior_match = (bar_dt, close_px)

    if exact_match is not None:
        return exact_match[1]
    if prior_match is not None:
        return prior_match[1]

    # Fall back strictly to a PRIOR trading day's EOD close (< day_et) to avoid same-day EOD lookahead.
    day_et = slot_dt_utc.astimezone(EASTERN_TZ).date().isoformat()
    ticker_daily = daily_closes.get(clean_ticker, {})
    prior_days = sorted(d for d in ticker_daily if d < day_et)
    if prior_days:
        return ticker_daily[prior_days[-1]]
    return None


def has_slot_bar(bars: list[dict[str, Any]], slot_dt_utc: datetime) -> bool:
    """True when cached intraday bars include a bar within 2h at or before slot_dt_utc."""
    for bar in bars:
        bar_dt = _parse_bar_dt_utc(bar.get("bar_time_utc"))
        if bar_dt is None:
            continue
        if 0 <= (slot_dt_utc - bar_dt).total_seconds() <= _PRIOR_BAR_MAX_AGE_SECONDS:
            return True
    return False


def merge_intraday_bars(existing: list[dict[str, Any]], fetched: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge intraday bars keyed by bar_time_utc sorted chronologically."""
    merged: dict[str, dict[str, Any]] = {str(b["bar_time_utc"]): b for b in existing if b.get("bar_time_utc")}
    for bar in fetched:
        if bar.get("bar_time_utc"):
            merged[str(bar["bar_time_utc"])] = bar
    return sorted(merged.values(), key=lambda b: str(b["bar_time_utc"]))


async def snapshot_live_intraday_bars(
    sb_client: Any,
    tickers: list[str],
    slot_dt_utc: datetime,
) -> int:
    """Record live slot prices for active recipe tickers + SPY in one batched upsert."""
    from tools._compat import MarketDataManager

    unique_tickers = sorted({t.upper().strip() for t in [*tickers, "SPY"] if t and t.strip()})
    if not unique_tickers or sb_client is None:
        return 0
    manager = MarketDataManager()
    ts_iso = slot_dt_utc.replace(second=0, microsecond=0).astimezone(UTC).isoformat()

    quotes = await asyncio.gather(*(manager.get_quote(tkr) for tkr in unique_tickers), return_exceptions=True)
    payload: list[dict[str, Any]] = []
    for tkr, quote in zip(unique_tickers, quotes, strict=True):
        if isinstance(quote, Exception):
            logger.warning("Failed snapshotting live intraday bar for %s", tkr, exc_info=quote)
            continue
        px = float(quote.price) if quote and quote.exists and quote.price else 0.0
        if px <= 0:
            continue
        payload.append(
            {
                "ticker": tkr,
                "bar_time_utc": ts_iso,
                "open": px,
                "high": px,
                "low": px,
                "close": px,
                "volume": 0,
                "source": "live_snapshot",
            }
        )

    if not payload:
        return 0
    try:
        sb_client.table("recipe_intraday_bars").upsert(payload, on_conflict="ticker,bar_time_utc").execute()
        return len(payload)
    except Exception:
        logger.warning("Failed batch upserting %d live intraday snapshots", len(payload), exc_info=True)
        return 0


def load_daily_closes(sb_client: Any, tickers: set[str], start_day: str, end_day: str) -> dict[str, dict[str, float]]:
    """Batch-fetch daily closing prices from price_history for traded tickers (with 7d prior lookback)."""
    if not tickers:
        return {}
    lookback_start = (datetime.fromisoformat(start_day[:10]) - timedelta(days=7)).date().isoformat()
    daily_close: dict[str, dict[str, float]] = {}
    try:
        res = (
            sb_client.table("price_history")
            .select("ticker, fetched_at, close, price")
            .in_("ticker", sorted(tickers))
            .gte("fetched_at", f"{lookback_start}T00:00:00+00:00")
            .lte("fetched_at", f"{end_day}T23:59:59+00:00")
            .order("fetched_at", desc=False)
            .limit(10000)
            .execute()
        )
        for row in res.data or []:
            day = str(row.get("fetched_at", ""))[:10]
            tkr = str(row.get("ticker", "")).upper().strip()
            raw_px = row.get("close") if row.get("close") is not None else row.get("price")
            if day and tkr and raw_px is not None:
                daily_close.setdefault(tkr, {})[day] = float(raw_px)
    except Exception:
        logger.exception("Failed fetching daily closes from price_history")
    return daily_close
