"""Market data transformation and validation logic.

Provides pure functions for date coverage validation of historical price bars
and pre-market quote synthesis with overnight gap calculations.
"""

import contextlib
import datetime
import math

from core.config import logger

from .providers.base import TickerData


def validate_date_coverage(rows: list, days_requested: int) -> tuple[bool, str]:
    """Validate that cached price history rows represent true historical data.

    Returns:
        tuple: (is_valid, reason) - is_valid is True if cache should be used
    """
    if not rows:
        return False, "no data"

    today = datetime.datetime.now(datetime.UTC).date().isoformat()
    distinct_dates = set()
    for row in rows:
        fetched_at = row.get("fetched_at", "")
        if fetched_at:
            date_part = fetched_at[:10]
            distinct_dates.add(date_part)

    distinct_count = len(distinct_dates)

    if distinct_count == 0:
        return False, "no valid dates"

    if all(d == today for d in distinct_dates):
        return False, f"all {distinct_count} rows from today"

    min_required_dates = max(2, math.ceil(days_requested / 2))
    if distinct_count < min_required_dates:
        return False, f"only {distinct_count} distinct dates, need {min_required_dates}"

    has_old_data = any(d != today for d in distinct_dates)
    if not has_old_data:
        return False, f"no historical data (all {distinct_count} dates are today)"

    # Check cache staleness: if the newest date in cache is > 4 calendar days old,
    # it's considered stale (e.g. over weekends/holidays is fine, but weeks is not).
    sorted_dates = sorted(list(distinct_dates), reverse=True)
    newest_date_str = sorted_dates[0]
    try:
        newest_date = datetime.date.fromisoformat(newest_date_str)
        today_date = datetime.datetime.now(datetime.UTC).date()
        age_days = (today_date - newest_date).days
        if age_days > 4:
            return False, f"cache is stale (newest entry from {newest_date_str} is {age_days} days old)"
    except Exception as e:
        logger.warning(f"Error validating price history cache staleness: {e}")

    return True, f"valid cache with {distinct_count} distinct dates"


def _extract_aftermarket_price(aftermarket_quote: dict | None) -> tuple[float | None, int | None]:
    """Extract positive price and volume from dedicated aftermarket quote dict."""
    if aftermarket_quote and aftermarket_quote.get("price"):
        with contextlib.suppress(ValueError, TypeError):
            cand_price = float(aftermarket_quote["price"])
            if cand_price > 0:
                return cand_price, aftermarket_quote.get("volume")
    return None, None


def _extract_history_prev_close(history: list[dict] | None) -> float | None:
    """Resolve previous close price from historical price bars."""
    if not history:
        return None
    sorted_hist = sorted(history, key=lambda x: x.get("fetched_at", ""))
    if sorted_hist:
        last_bar = sorted_hist[-1]
        close_cand = last_bar.get("close") or last_bar.get("price")
        if close_cand is not None:
            with contextlib.suppress(ValueError, TypeError):
                return float(close_cand)
    return None


def compute_premarket_quote(
    quote: TickerData | None,
    aftermarket_quote: dict | None = None,
    history: list[dict] | None = None,
) -> dict | None:
    """Synthesize a pre-market quote combining aftermarket data, quotes, and history fallback.

    Args:
        quote: Standard quote object (if available).
        aftermarket_quote: Dedicated aftermarket / pre-market quote dict (if supported).
        history: Recent price history bars (used as fallback for previous close).

    Returns:
        Standardized premarket quote dict with price, previous_close, change, change_pct, and volume.
    """
    pm_price, volume = _extract_aftermarket_price(aftermarket_quote)
    prev_close = None
    change = None
    change_pct = None

    # 2. Standard quote fallback/augmentation
    if quote:
        if pm_price is not None:
            if quote.price and quote.price > 0:
                prev_close = quote.price
            elif quote.previous_close and quote.previous_close > 0:
                prev_close = quote.previous_close
        else:
            if quote.price and quote.price > 0:
                pm_price = quote.price
                change = quote.change
                change_pct = quote.change_pct
            if quote.previous_close and quote.previous_close > 0:
                prev_close = quote.previous_close
            if volume is None:
                volume = quote.volume

    if pm_price is None or pm_price <= 0:
        return None

    # 3. If previous close is still missing, fall back to recent history
    if prev_close is None or prev_close <= 0:
        prev_close = _extract_history_prev_close(history)

    if not prev_close or prev_close <= 0:
        prev_close = pm_price

    if change is None:
        change = pm_price - prev_close
    if change_pct is None:
        change_pct = (change / prev_close) * 100.0 if prev_close else 0.0

    res = {
        "price": pm_price,
        "previous_close": prev_close,
        "change": change,
        "change_pct": change_pct,
    }
    if volume is not None:
        res["volume"] = volume

    return res


def _sort_and_filter_history(history: list[dict] | None) -> list[dict]:
    """Extract valid positive price bars sorted in ascending chronological order."""
    if not history:
        return []
    valid_bars = []
    for b in history:
        p_val = b.get("price") if b.get("price") is not None else b.get("close")
        if p_val is not None:
            try:
                p = float(p_val)
                if not math.isnan(p) and p > 0:
                    valid_bars.append(b)
            except (ValueError, TypeError):
                continue
    valid_bars.sort(key=lambda x: str(x.get("date", "") or x.get("fetched_at", "") or x.get("timestamp", "")))
    return valid_bars


def _resolve_prior_close(
    sorted_bars: list[dict],
    current_price: float,
    target_prefix: str,
) -> float | None:
    """Find the most recent closing price strictly prior to the target session."""
    prior_bars = [
        b
        for b in sorted_bars
        if str(b.get("date", "") or b.get("fetched_at", "") or b.get("timestamp", ""))[:10] < target_prefix
    ]
    if not prior_bars and len(sorted_bars) >= 2:
        last_p = float(sorted_bars[-1].get("close") or sorted_bars[-1].get("price", 0))
        prior_bars = sorted_bars[:-1] if abs(last_p - current_price) < 1e-4 else sorted_bars

    if prior_bars:
        p_prior = float(prior_bars[-1].get("close") or prior_bars[-1].get("price", 0))
        if p_prior > 0 and not math.isnan(p_prior):
            return p_prior
    return None


def _derive_from_history(
    sorted_bars: list[dict],
    target_prefix: str,
) -> tuple[float | None, float | None, int | None]:
    """Derive session price, prior close, and volume from historical bars up to target_prefix."""
    eligible_bars = [
        b
        for b in sorted_bars
        if str(b.get("date", "") or b.get("fetched_at", "") or b.get("timestamp", ""))[:10] <= target_prefix
    ]
    if not eligible_bars:
        return None, None, None

    latest_bar = eligible_bars[-1]
    price = float(latest_bar.get("close") or latest_bar.get("price", 0))
    volume = latest_bar.get("volume")

    prior_close = _resolve_prior_close(eligible_bars, price, target_prefix)
    return price, prior_close, volume


def compute_reference_quote(
    quote: TickerData | None,
    history: list[dict] | None = None,
    target_date: str | None = None,
) -> dict | None:
    """Synthesize a session reference quote with verified 1D price and change percentage.

    Args:
        quote: Standard quote object (if available).
        history: Historical price bars (OHLCV).
        target_date: Optional session date string ('YYYY-MM-DD'). Bars >= target_date are excluded
                     when searching for prior close.

    Returns:
        Standardized reference quote dict with price, previous_close, change, change_pct, and volume.
    """
    sorted_bars = _sort_and_filter_history(history)
    today_iso = datetime.datetime.now(datetime.UTC).date().isoformat()
    target_prefix = target_date[:10] if target_date else today_iso
    is_historical = target_prefix < today_iso

    price = None
    prev_close = None
    change = None
    change_pct = None
    volume = None

    # For live/today runs, prefer real-time quote if available
    if not is_historical and quote and quote.price and not math.isnan(quote.price) and quote.price > 0:
        price = quote.price
        prev_close = quote.previous_close
        change = quote.change
        change_pct = quote.change_pct
        volume = quote.volume

    # If quote is missing, invalid, or evaluating historical target date, derive from history
    if price is None and sorted_bars:
        price, prev_close, volume = _derive_from_history(sorted_bars, target_prefix)

    # If previous_close or change_pct is missing on the quote, resolve strictly prior bar from history
    if (prev_close is None or change_pct is None) and price is not None and sorted_bars:
        resolved_prev = _resolve_prior_close(sorted_bars, price, target_prefix)
        if resolved_prev is not None:
            prev_close = resolved_prev

    if price is None or math.isnan(price) or price <= 0:
        return None

    if prev_close is not None and (math.isnan(prev_close) or prev_close <= 0):
        prev_close = None
        change = None
        change_pct = None

    if prev_close and prev_close > 0 and change_pct is None:
        change = price - prev_close
        change_pct = (change / prev_close) * 100.0

    res = {
        "price": price,
        "previous_close": prev_close,
        "change": change,
        "change_pct": change_pct,
    }
    if volume is not None:
        res["volume"] = volume
    return res
