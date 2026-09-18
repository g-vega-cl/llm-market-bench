"""Economic data releases client and real-time macro calendar integration.

Fetches scheduled and released economic indicators (CPI, PPI, Nonfarm Payrolls,
Retail Sales, GDP, etc.) from Financial Modeling Prep (FMP), calculates economic
surprises (actual vs. consensus), and provides structured summaries for market
predictors, newsletter synthesis, and autonomous research agents.
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from core.config import FMP_API_KEY

logger = logging.getLogger("engine")

FMP_ECONOMIC_CALENDAR_URL = "https://financialmodelingprep.com/stable/economic-calendar"
DEFAULT_CACHE_TTL_SECONDS = 1800  # 30-minute cache requested for economic calendar


@dataclass
class EconomicEvent:
    """Structured representation of an economic calendar indicator release."""

    date: str
    time_et: str
    country: str
    event: str
    impact: str
    actual: float | None
    estimate: float | None
    previous: float | None
    change: float | None
    status: str
    surprise: float | None
    currency: str | None = None
    change_pct: float | None = None


# In-memory cache keyed by (from_date, to_date, country)
_cache: dict[str, dict[str, Any]] = {}


def _parse_time_et(date_str: str) -> str:
    """Extracts Eastern Time representation from FMP timestamp.

    FMP timestamps are in UTC ('YYYY-MM-DD HH:MM:SS').
    """
    if not date_str:
        return "N/A"
    try:
        clean_str = date_str.strip()
        if " " in clean_str:
            utc_dt = datetime.strptime(clean_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            et_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))
            return et_dt.strftime("%H:%M ET")
        return clean_str
    except Exception:
        return date_str.split(" ")[-1] if " " in date_str else date_str


async def fetch_economic_calendar_events(
    from_date: str,
    to_date: str,
    country: str | None = "US",
    force_refresh: bool = False,
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
) -> list[EconomicEvent]:
    """Fetches economic calendar events from FMP for a specified date range.

    Args:
        from_date: Start date string (YYYY-MM-DD).
        to_date: End date string (YYYY-MM-DD).
        country: Optional country filter (defaults to 'US'). Pass None for all countries.
        force_refresh: If True, bypass in-memory cache.
        cache_ttl_seconds: In-memory cache duration (default 1800s / 30 mins).

    Returns:
        List of structured EconomicEvent instances.
    """
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY is not configured; economic calendar releases cannot be fetched.")
        return []

    cache_key = f"{from_date}:{to_date}:{country or 'ALL'}"
    now_ts = time.time()

    if not force_refresh and cache_key in _cache:
        entry = _cache[cache_key]
        if now_ts - entry["timestamp"] < cache_ttl_seconds:
            return entry["events"]

    params: dict[str, Any] = {
        "apikey": FMP_API_KEY,
        "from": from_date,
        "to": to_date,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(FMP_ECONOMIC_CALENDAR_URL, params=params)
            if resp.status_code != 200:
                logger.error(
                    "FMP Economic Calendar API returned status %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return []

            raw_data = resp.json()
            if not isinstance(raw_data, list):
                logger.warning("FMP Economic Calendar unexpected response format: %s", type(raw_data))
                return []

            events: list[EconomicEvent] = []
            for item in raw_data:
                item_country = (item.get("country") or "").strip()
                if country and item_country.upper() != country.upper():
                    continue

                actual = item.get("actual")
                actual_val = float(actual) if actual is not None and str(actual).strip() not in ("", ".") else None

                estimate = item.get("estimate")
                est_val = float(estimate) if estimate is not None and str(estimate).strip() not in ("", ".") else None

                previous = item.get("previous")
                prev_val = float(previous) if previous is not None and str(previous).strip() not in ("", ".") else None

                change = item.get("change")
                chg_val = float(change) if change is not None and str(change).strip() not in ("", ".") else None

                date_raw = str(item.get("date", ""))
                time_et = _parse_time_et(date_raw)

                status = "RELEASED" if actual_val is not None else "PENDING"
                surprise = (actual_val - est_val) if (actual_val is not None and est_val is not None) else None

                chg_pct = item.get("changePercentage")
                chg_pct_val = float(chg_pct) if chg_pct is not None and str(chg_pct).strip() not in ("", ".") else None

                events.append(
                    EconomicEvent(
                        date=date_raw,
                        time_et=time_et,
                        country=item_country or "US",
                        event=str(item.get("event", "Economic Release")).strip(),
                        impact=str(item.get("impact", "Medium")).strip().capitalize(),
                        actual=actual_val,
                        estimate=est_val,
                        previous=prev_val,
                        change=chg_val,
                        status=status,
                        surprise=surprise,
                        currency=item.get("currency"),
                        change_pct=chg_pct_val,
                    )
                )

            # Sort events chronologically, then high impact first
            impact_weight = {"High": 3, "Medium": 2, "Low": 1}
            events.sort(key=lambda e: (e.date, -impact_weight.get(e.impact, 0)))

            _cache[cache_key] = {"timestamp": now_ts, "events": events}
            return events

    except Exception as e:
        logger.exception("Error fetching economic calendar from FMP: %s", e)
        return []


def format_economic_events_markdown(events: list[EconomicEvent], header_label: str = "TODAY'S") -> str:
    """Formats a list of EconomicEvents into a clean, dense terminal/markdown summary."""
    if not events:
        return ""

    released = [e for e in events if e.status == "RELEASED"]
    pending = [e for e in events if e.status == "PENDING"]

    lines = [f"=== {header_label.upper()} ECONOMIC RELEASES & MACRO PRINTS (Live Actual vs Consensus) ==="]

    if released:
        lines.append("Active Released Catalysts:")
        for e in released:
            est_str = f"{e.estimate:,.2f}" if e.estimate is not None else "N/A"
            act_str = f"{e.actual:,.2f}" if e.actual is not None else "N/A"
            prev_str = f"{e.previous:,.2f}" if e.previous is not None else "N/A"

            surprise_str = ""
            if e.surprise is not None:
                sign = "+" if e.surprise > 0 else ""
                surprise_str = f" | Surprise: {sign}{e.surprise:,.2f}"

            lines.append(
                f"- [{e.time_et}] {e.country} {e.event}: Actual {act_str} vs Est {est_str} (Prev {prev_str}){surprise_str} "
                f"[Impact: {e.impact.upper()} | Status: RELEASED]"
            )

    if pending:
        lines.append("Pending Upcoming Releases:")
        for e in pending:
            est_str = f"{e.estimate:,.2f}" if e.estimate is not None else "N/A"
            prev_str = f"{e.previous:,.2f}" if e.previous is not None else "N/A"
            lines.append(
                f"- [{e.time_et}] {e.country} {e.event}: Est {est_str} | Prev {prev_str} "
                f"[Impact: {e.impact.upper()} | Status: PENDING]"
            )

    lines.append("===========================================================================")
    return "\n".join(lines)


async def get_today_economic_releases_summary(
    target_date: str | None = None,
    country: str | None = "US",
    force_refresh: bool = False,
) -> str:
    """Convenience helper to retrieve and format today's economic releases in Eastern Time.

    Args:
        target_date: Optional date string (YYYY-MM-DD). Defaults to today in Eastern Time.
        country: Country filter (defaults to 'US').
        force_refresh: If True, bypass cache.

    Returns:
        Formatted markdown block of released and pending events, or empty string if none.
    """
    if not target_date:
        now_et = datetime.now(ZoneInfo("America/New_York"))
        target_date = now_et.date().isoformat()

    events = await fetch_economic_calendar_events(
        from_date=target_date,
        to_date=target_date,
        country=country,
        force_refresh=force_refresh,
    )

    if not events:
        return ""

    return format_economic_events_markdown(events, header_label="TODAY'S")
