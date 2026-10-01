"""US equity market session, calendar, and trading hours manager.

Coordinates market hours detection, holiday tracking, and trading day validation
with in-memory locking and caching to avoid redundant API hits.
"""

import asyncio
import datetime
from zoneinfo import ZoneInfo

from core.config import FMP_API_KEY as DEFAULT_FMP_API_KEY
from core.config import logger


class MarketSessionManager:
    """Manages US equity market session status, holidays, and schedule checks."""

    _market_status_cache: dict = {
        "is_open": None,
        "fetched_at": None,
        "ttl_seconds": 1800,  # 30 minutes
    }
    _market_status_lock: asyncio.Lock | None = None

    _holidays_cache: dict = {
        "holidays": None,
        "fetched_at": None,
        "ttl_seconds": 86400,  # 24 hours
    }
    _holidays_lock: asyncio.Lock | None = None

    def __init__(self, fmp_api_key: str | None = None):
        self.fmp_api_key = fmp_api_key if fmp_api_key is not None else DEFAULT_FMP_API_KEY

    async def is_market_open(self, fmp_api_key: str | None = None) -> bool:
        """Checks if the US stock market (NASDAQ/NYSE) is currently open.

        Prioritizes FMP API for holiday awareness, falls back to time-based check.
        Uses class-level cache to avoid repeated API calls within the same run.
        """
        api_key = fmp_api_key if fmp_api_key is not None else self.fmp_api_key
        now = datetime.datetime.now(datetime.UTC)
        cache = self._market_status_cache

        if cache["fetched_at"] is not None:
            elapsed = (now - cache["fetched_at"]).total_seconds()
            if elapsed < cache["ttl_seconds"]:
                logger.debug(f"Using cached market status: {'OPEN' if cache['is_open'] else 'CLOSED'}")
                return cache["is_open"]

        if MarketSessionManager._market_status_lock is None:
            MarketSessionManager._market_status_lock = asyncio.Lock()

        async with MarketSessionManager._market_status_lock:
            # Recheck cache after acquiring lock
            if cache["fetched_at"] is not None:
                elapsed = (now - cache["fetched_at"]).total_seconds()
                if elapsed < cache["ttl_seconds"]:
                    return cache["is_open"]

            try:
                now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
            except Exception:
                now_et = datetime.datetime.now()
                logger.warning("zoneinfo America/New_York failed, using local time for market hours baseline.")

            # 1. Primary Check: FMP API (Handles Holidays)
            if api_key:
                try:
                    import httpx

                    async with httpx.AsyncClient() as client:
                        url = "https://financialmodelingprep.com/stable/exchange-market-hours"
                        params = {"exchange": "NASDAQ", "apikey": api_key}
                        resp = await client.get(url, params=params)
                        resp.raise_for_status()
                        data = resp.json()

                        if data and isinstance(data, list):
                            is_open = data[0].get("isMarketOpen", False)
                            logger.info(f"FMP Market Status (NASDAQ): {'OPEN' if is_open else 'CLOSED'}")

                            # Fallback to time-based override for transient API cache lag right at market open
                            # (9:30 AM - 9:50 AM ET on weekdays)
                            if not is_open:
                                try:
                                    now_et_check = datetime.datetime.now(ZoneInfo("America/New_York"))
                                except Exception:
                                    now_et_check = datetime.datetime.now()

                                if now_et_check.weekday() < 5:
                                    market_open_threshold = now_et_check.replace(
                                        hour=9, minute=30, second=0, microsecond=0
                                    )
                                    buffer_end = now_et_check.replace(hour=9, minute=50, second=0, microsecond=0)
                                    if market_open_threshold <= now_et_check <= buffer_end:
                                        logger.info(
                                            "FMP reported CLOSED, but time is within the market-open buffer (9:30-9:50 AM ET) on a weekday. Overriding to OPEN."
                                        )
                                        is_open = True

                            cache["is_open"] = is_open
                            cache["fetched_at"] = datetime.datetime.now(datetime.UTC)
                            return is_open
                except Exception as e:
                    logger.warning(f"Failed to fetch market status from FMP: {e}. Falling back to time-based check.")

            # 2. Fallback Check: Time-based (Mon-Fri, 09:30-16:00 ET)
            if now_et.weekday() >= 5:
                result = False
            else:
                market_start = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
                market_end = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
                result = market_start <= now_et <= market_end

            cache["is_open"] = result
            cache["fetched_at"] = datetime.datetime.now(datetime.UTC)
            return result

    async def get_market_holidays(self, fmp_api_key: str | None = None) -> list[dict]:
        """Fetch US market holidays from FMP API with in-memory caching."""
        api_key = fmp_api_key if fmp_api_key is not None else self.fmp_api_key
        now = datetime.datetime.now(datetime.UTC)
        cache = self._holidays_cache

        if cache["holidays"] is not None and cache["fetched_at"] is not None:
            elapsed = (now - cache["fetched_at"]).total_seconds()
            if elapsed < cache["ttl_seconds"]:
                return cache["holidays"]

        if MarketSessionManager._holidays_lock is None:
            MarketSessionManager._holidays_lock = asyncio.Lock()

        async with MarketSessionManager._holidays_lock:
            if cache["holidays"] is not None and cache["fetched_at"] is not None:
                elapsed = (now - cache["fetched_at"]).total_seconds()
                if elapsed < cache["ttl_seconds"]:
                    return cache["holidays"]

            holidays: list[dict] = []
            if api_key:
                try:
                    import httpx

                    async with httpx.AsyncClient() as client:
                        url = "https://financialmodelingprep.com/stable/holidays-by-exchange"
                        params = {"exchange": "NASDAQ", "apikey": api_key}
                        resp = await client.get(url, params=params, timeout=10.0)
                        resp.raise_for_status()
                        data = resp.json()
                        if isinstance(data, list):
                            holidays = data
                except Exception as e:
                    logger.warning(f"Failed to fetch market holidays from FMP: {e}")

            cache["holidays"] = holidays
            cache["fetched_at"] = datetime.datetime.now(datetime.UTC)
            return holidays

    @staticmethod
    def is_known_us_market_holiday_fallback(date_obj: datetime.date) -> bool:
        """Rule-based fallback for US stock exchange holidays when API data is unavailable."""
        month = date_obj.month
        day = date_obj.day
        weekday = date_obj.weekday()  # Monday=0, Sunday=6

        return bool(
            # New Year's Day (Jan 1, observed Jan 2 if Sun)
            (month == 1 and day == 1)
            or (month == 1 and day == 2 and weekday == 0)
            # Martin Luther King Jr. Day (Third Monday in January)
            or (month == 1 and weekday == 0 and 15 <= day <= 21)
            # Washington's Birthday / Presidents' Day (Third Monday in February)
            or (month == 2 and weekday == 0 and 15 <= day <= 21)
            # Memorial Day (Last Monday in May)
            or (month == 5 and weekday == 0 and day >= 25)
            # Juneteenth (June 19, observed June 20 if Sun, June 18 if Sat)
            or (month == 6 and day == 19)
            or (month == 6 and day == 20 and weekday == 0)
            or (month == 6 and day == 18 and weekday == 4)
            # Independence Day (July 4, observed July 5 if Sun, July 3 if Sat)
            or (month == 7 and day == 4)
            or (month == 7 and day == 5 and weekday == 0)
            or (month == 7 and day == 3 and weekday == 4)
            # Labor Day (First Monday in September)
            or (month == 9 and weekday == 0 and 1 <= day <= 7)
            # Thanksgiving Day (Fourth Thursday in November)
            or (month == 11 and weekday == 3 and 22 <= day <= 28)
            # Christmas Day (Dec 25, observed Dec 26 if Sun, Dec 24 if Sat)
            or (month == 12 and day == 25)
            or (month == 12 and day == 26 and weekday == 0)
            or (month == 12 and day == 24 and weekday == 4)
        )

    async def is_trading_day(
        self,
        target_date: datetime.date | datetime.datetime | str | None = None,
        fmp_api_key: str | None = None,
    ) -> bool:
        """Checks if a given date is an active US equity trading day (non-weekend, non-holiday).

        Args:
            target_date: Target date to check (datetime.date, ISO string YYYY-MM-DD, or None for today ET).
            fmp_api_key: Optional FMP API key override.

        Returns:
            True if target_date is a regular trading session, False if weekend or market holiday.
        """
        if target_date is None:
            try:
                date_obj = datetime.datetime.now(ZoneInfo("America/New_York")).date()
            except Exception:
                date_obj = datetime.datetime.now().date()
        elif isinstance(target_date, str):
            date_obj = datetime.date.fromisoformat(target_date[:10])
        elif isinstance(target_date, datetime.datetime):
            date_obj = target_date.date()
        else:
            date_obj = target_date

        # 1. Weekends (Saturday=5, Sunday=6)
        if date_obj.weekday() >= 5:
            return False

        # 2. Check market holidays from FMP
        date_str = date_obj.isoformat()
        try:
            holidays = await self.get_market_holidays(fmp_api_key=fmp_api_key)
            for h in holidays:
                if h.get("date") == date_str and h.get("isClosed", True):
                    return False
        except Exception as e:
            logger.warning(f"Error checking market holiday for {date_str}: {e}")

        # 3. Rule-based US market holiday fallback
        return not self.is_known_us_market_holiday_fallback(date_obj)

    @staticmethod
    async def is_premarket() -> bool:
        """Checks if currently in US pre-market trading session (Mon-Fri 04:00 - 09:30 ET).

        Returns False on weekends.
        """
        try:
            now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
        except Exception:
            now_et = datetime.datetime.now()

        # Weekends
        if now_et.weekday() >= 5:
            return False

        premarket_start = now_et.replace(hour=4, minute=0, second=0, microsecond=0)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)

        return premarket_start <= now_et < market_open
