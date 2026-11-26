"""US equity market session manager.

Adapter over :mod:`trading.market_calendar`. This class used to own its own
holiday knowledge — an FMP fetch plus hand-rolled rules — which duplicated and
disagreed with the Alpaca-backed gate the live trader uses. `MarketCalendar` is
now the single implementation: /v2/clock and /v2/calendar when a trading client
is wired, the same rule set as the offline fallback otherwise.

The async surface is kept because `execution/market_data.py` and
`recipes/runner.py` await it; each call runs the bounded calendar lookup on a
worker thread so callers never block their event loop.
"""

import asyncio
import datetime
from zoneinfo import ZoneInfo

from trading.market_calendar import get_market_calendar, is_known_us_market_holiday

ET = ZoneInfo("America/New_York")


class MarketSessionManager:
    """Delegating session manager kept for its async API and class attributes."""

    # Retained for attribute compatibility: market_data.py proxies these.
    _market_status_cache: dict = {}
    _holidays_cache: dict = {}
    _market_status_lock: asyncio.Lock | None = None
    _holidays_lock: asyncio.Lock | None = None

    def __init__(self, fmp_api_key: str | None = None):
        # Kept in the signature so existing callers keep working; unused.
        self.fmp_api_key = fmp_api_key

    async def is_market_open(self, fmp_api_key: str | None = None) -> bool:
        """Whether the regular US session is running right now."""
        return await asyncio.to_thread(get_market_calendar().is_open)

    async def get_market_holidays(self, fmp_api_key: str | None = None) -> list[dict]:
        """Non-session weekdays for the next 30 days, derived from the calendar."""
        calendar = get_market_calendar()
        today = datetime.datetime.now(ET).date()
        days = [today + datetime.timedelta(days=offset) for offset in range(1, 31)]
        sessions = await asyncio.gather(*(asyncio.to_thread(calendar.session_for, day) for day in days))
        return [
            {"date": day.isoformat(), "exchange": "NYSE", "isClosed": True}
            for day, session in zip(days, sessions, strict=True)
            if day.weekday() < 5 and session is None
        ]

    @staticmethod
    def is_known_us_market_holiday_fallback(date_obj: datetime.date) -> bool:
        """Offline holiday check (rule-based, no network)."""
        return is_known_us_market_holiday(date_obj)

    async def is_trading_day(
        self,
        target_date: datetime.date | datetime.datetime | str | None = None,
        fmp_api_key: str | None = None,
    ) -> bool:
        """Whether `target_date` is a regular session day (defaults to today ET)."""
        if target_date is None:
            date_obj = datetime.datetime.now(ET).date()
        elif isinstance(target_date, str):
            date_obj = datetime.date.fromisoformat(target_date[:10])
        elif isinstance(target_date, datetime.datetime):
            date_obj = target_date.date()
        else:
            date_obj = target_date

        session = await asyncio.to_thread(get_market_calendar().session_for, date_obj)
        return session is not None

    @staticmethod
    async def is_premarket() -> bool:
        """Whether it is 04:00-09:30 ET on a weekday."""
        now_et = datetime.datetime.now(ET)
        if now_et.weekday() >= 5:
            return False

        premarket_start = now_et.replace(hour=4, minute=0, second=0, microsecond=0)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        return premarket_start <= now_et < market_open
