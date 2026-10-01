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
    pm_price = None
    prev_close = None
    change = None
    change_pct = None
    volume = None

    # 1. Dedicated aftermarket / pre-market quote from provider if available
    if aftermarket_quote and aftermarket_quote.get("price"):
        with contextlib.suppress(ValueError, TypeError):
            cand_price = float(aftermarket_quote["price"])
            if cand_price > 0:
                pm_price = cand_price
                volume = aftermarket_quote.get("volume")

    # 2. Standard quote fallback/augmentation
    if quote:
        if pm_price is not None:
            # We have a dedicated aftermarket/premarket quote (pm_price).
            # In pre-market, quote.price represents the prior regular session close.
            if quote.price and quote.price > 0:
                prev_close = quote.price
            elif quote.previous_close and quote.previous_close > 0:
                prev_close = quote.previous_close
        else:
            # No dedicated aftermarket quote available; use standard quote
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
    if (prev_close is None or prev_close <= 0) and history:
        sorted_hist = sorted(history, key=lambda x: x.get("fetched_at", ""))
        if sorted_hist:
            last_bar = sorted_hist[-1]
            close_cand = last_bar.get("close") or last_bar.get("price")
            if close_cand is not None:
                with contextlib.suppress(ValueError, TypeError):
                    prev_close = float(close_cand)

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
