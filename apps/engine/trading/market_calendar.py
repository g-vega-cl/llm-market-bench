"""Authoritative US equity session calendar.

`MarketCalendar.is_open` answers "is the regular session running right now".
With a trading client it asks Alpaca's `/v2/clock`, which already knows market
holidays, half-day early closes and ad-hoc closures — the weekday + 09:30-16:00
ET arithmetic does not, and reported the market as open on Thanksgiving.

Policy (decided deliberately):

- no client (local dev, unit tests, audit harness) -> weekday/time arithmetic;
- client present but the clock cannot be read -> **closed**, so a network blip
  skips a session instead of trading into a holiday;
- the clock answer is cached for `ttl_seconds` (default 60) because the gate is
  consulted every 10 seconds by the tape poller.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger("engine")

ET = ZoneInfo("America/New_York")
REGULAR_OPEN_MINUTES = 570  # 09:30 ET
DEFAULT_TTL_SECONDS = 60.0
DEFAULT_CALL_TIMEOUT_SECONDS = 5.0

# alpaca-py's requests transport sets no timeout, and the gate is consulted from
# a 10-second loop on the daemon's single event loop: one hung TLS connection
# would freeze the tape broadcast, the agent turn and the QA worker. Every SDK
# call therefore runs on a one-worker pool with a hard bound.
#
# A timed-out task is NOT cancelled (the SDK call cannot be interrupted), so the
# worker stays busy forever. On timeout the pool is therefore discarded and
# rebuilt: the hung thread is abandoned, every later caller gets a fresh worker,
# and the failure costs one thread per hang instead of a dead gate for the
# lifetime of the process.
_EXECUTOR_LOCK = threading.Lock()
_CALL_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="market-calendar")


def _call_bounded(fn: Any, timeout: float) -> Any:
    """Run one SDK call on the shared worker, replacing the worker on timeout."""
    global _CALL_EXECUTOR
    executor = _CALL_EXECUTOR
    try:
        return executor.submit(fn).result(timeout=timeout)
    except FuturesTimeout:
        with _EXECUTOR_LOCK:
            if _CALL_EXECUTOR is executor:
                _CALL_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="market-calendar")
        executor.shutdown(wait=False)
        raise TimeoutError(f"market calendar call exceeded {timeout:.1f}s") from None


def _as_et(now_dt: datetime) -> datetime:
    """Treat a naive datetime as Eastern; leave aware values untouched."""
    return now_dt if now_dt.tzinfo is not None else now_dt.replace(tzinfo=ET)


def is_known_us_market_holiday(day: date) -> bool:
    """Rule-based US exchange holiday check, used when no Alpaca client is available.

    Covers New Year, MLK, Presidents' Day, Good Friday, Memorial Day, Juneteenth,
    Independence Day, Labor Day, Thanksgiving and Christmas with their observed
    shifts. It is the offline fallback only — the exchange calendar is
    authoritative whenever a client is wired.
    """
    month = day.month
    day_of_month = day.day
    weekday = day.weekday()  # Monday=0, Sunday=6

    return bool(
        # New Year's Day (Jan 1, observed Jan 2 if Sun)
        (month == 1 and day_of_month == 1)
        or (month == 1 and day_of_month == 2 and weekday == 0)
        # Martin Luther King Jr. Day (third Monday in January)
        or (month == 1 and weekday == 0 and 15 <= day_of_month <= 21)
        # Washington's Birthday (third Monday in February)
        or (month == 2 and weekday == 0 and 15 <= day_of_month <= 21)
        # Good Friday
        or day == _good_friday(day.year)
        # Memorial Day (last Monday in May)
        or (month == 5 and weekday == 0 and day_of_month >= 25)
        # Juneteenth (Jun 19, observed Jun 20 if Sun, Jun 18 if Sat)
        or (month == 6 and day_of_month == 19)
        or (month == 6 and day_of_month == 20 and weekday == 0)
        or (month == 6 and day_of_month == 18 and weekday == 4)
        # Independence Day (Jul 4, observed Jul 5 if Sun, Jul 3 if Sat)
        or (month == 7 and day_of_month == 4)
        or (month == 7 and day_of_month == 5 and weekday == 0)
        or (month == 7 and day_of_month == 3 and weekday == 4)
        # Labor Day (first Monday in September)
        or (month == 9 and weekday == 0 and 1 <= day_of_month <= 7)
        # Thanksgiving (fourth Thursday in November)
        or (month == 11 and weekday == 3 and 22 <= day_of_month <= 28)
        # Christmas (Dec 25, observed Dec 26 if Sun, Dec 24 if Sat)
        or (month == 12 and day_of_month == 25)
        or (month == 12 and day_of_month == 26 and weekday == 0)
        or (month == 12 and day_of_month == 24 and weekday == 4)
    )


def _good_friday(year: int) -> date:
    """Western Easter (anonymous Gregorian algorithm) minus two days."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    lam = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lam) // 451
    month = (h + lam - 7 * m + 114) // 31
    dom = ((h + lam - 7 * m + 114) % 31) + 1
    return date(year, month, dom) - timedelta(days=2)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The nth given weekday of a month (e.g. 4th Thursday of November)."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _local_close_time(day: date) -> time:
    """13:00 ET on the regular early-close days, 16:00 otherwise.

    The offline rules cannot know ad-hoc closures, but the scheduled half days
    are fixed: the day after Thanksgiving, July 3 and December 24 on a weekday.
    """
    day_after_thanksgiving = _nth_weekday(day.year, 11, 3, 4) + timedelta(days=1)
    is_early_close = day == day_after_thanksgiving or (day.month in (7, 12) and day.day in (3, 24))
    return time(13, 0) if is_early_close else time(16, 0)


def _local_is_session_day(day: date) -> bool:
    return day.weekday() < 5 and not is_known_us_market_holiday(day)


def _local_is_open(now_dt: datetime) -> bool:
    """Weekday + regular-hours arithmetic with the offline holiday rules."""
    weekday = now_dt.weekday() if callable(getattr(now_dt, "weekday", None)) else getattr(now_dt, "weekday", 0)
    if weekday >= 5:
        return False
    if is_known_us_market_holiday(now_dt.date()):
        return False

    hour = getattr(now_dt, "hour", 0)
    minute = getattr(now_dt, "minute", 0)
    close = _local_close_time(now_dt.date())
    return REGULAR_OPEN_MINUTES <= hour * 60 + minute < close.hour * 60 + close.minute


def _local_seconds_to_next_open(now_dt: datetime) -> float:
    """Seconds until the next 09:30 ET on a trading day (offline rules)."""
    today = now_dt.date()
    for offset in range(0, 10):
        day = today + timedelta(days=offset)
        if not _local_is_session_day(day):
            continue
        open_at = _at(day, time(9, 30))
        delta = (open_at - _as_et(now_dt)).total_seconds()
        if delta > 0:
            return float(delta)
    return 86_400.0


def _at(day: date, value: time) -> datetime:
    return datetime.combine(day, value, tzinfo=ET)


def _coerce_et(day: date, value: Any) -> datetime | None:
    """Turn an Alpaca calendar field (time or datetime) into an ET-aware datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=ET)
    if isinstance(value, time):
        return _at(day, value)
    return None


class MarketCalendar:
    """Regular-session gate backed by Alpaca's clock when a client is supplied."""

    def __init__(
        self,
        client: Any = None,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        call_timeout_seconds: float = DEFAULT_CALL_TIMEOUT_SECONDS,
    ):
        self._client = client
        self._ttl = float(ttl_seconds)
        self._timeout = float(call_timeout_seconds)
        self._clock: Any = None
        self._fetched_at: datetime | None = None
        self._failed = False
        self._sessions: dict[date, tuple[datetime, datetime] | None] = {}
        self._session_error_at: datetime | None = None
        self._lock = threading.Lock()

    def _call(self, fn: Any) -> Any:
        """Run one SDK call off-thread with a hard timeout (see _call_bounded)."""
        return _call_bounded(fn, self._timeout)

    @property
    def client(self) -> Any:
        return self._client

    def _read_clock(self, now_dt: datetime) -> Any | None:
        """Cached `/v2/clock`; returns None when the fetch failed or is unavailable."""
        now_dt = _as_et(now_dt)
        if self._fetched_at is not None:
            age = (now_dt - self._fetched_at).total_seconds()
            if 0 <= age < self._ttl:
                return None if self._failed else self._clock

        with self._lock:
            # Re-check: concurrent callers (asyncio.to_thread) must not stampede.
            if self._fetched_at is not None:
                age = (now_dt - self._fetched_at).total_seconds()
                if 0 <= age < self._ttl:
                    return None if self._failed else self._clock

            try:
                self._clock = self._call(self._client.get_clock)
                self._failed = False
            except Exception as exc:
                logger.warning(f"[MarketCalendar] get_clock failed; treating session as closed: {exc}")
                self._clock = None
                self._failed = True

            self._fetched_at = now_dt
            return None if self._failed else self._clock

    def is_open(self, now_dt: datetime | None = None) -> bool:
        """True only when the regular session is running right now."""
        now_dt = _as_et(now_dt or datetime.now(ET))

        if self._client is None:
            return _local_is_open(now_dt)

        clock = self._read_clock(now_dt)
        if clock is None:
            return False

        # A cached clock can outlive its own close (read at 15:59:30, still
        # served at 16:00:20). Alpaca queues orders submitted while closed, so
        # trust the payload's next_close rather than shrinking the TTL.
        if not bool(getattr(clock, "is_open", False)):
            return False
        next_close = getattr(clock, "next_close", None)
        if isinstance(next_close, datetime):
            return now_dt < _as_et(next_close)
        return True

    def seconds_to_next_open(self, now_dt: datetime | None = None) -> float:
        """Seconds until the next regular session open."""
        now_dt = _as_et(now_dt or datetime.now(ET))

        if self._client is not None:
            clock = self._read_clock(now_dt)
            next_open = getattr(clock, "next_open", None) if clock is not None else None
            if isinstance(next_open, datetime):
                return max(0.0, (_as_et(next_open) - now_dt).total_seconds())

        return _local_seconds_to_next_open(now_dt)

    def session_for(self, day: date) -> tuple[datetime, datetime] | None:
        """Regular session (open, close) in ET for `day`, or None when the market is shut.

        Uses Alpaca's /v2/calendar, which omits holidays and reports the early
        close on half days. Cached per day because the strategy hooks ask on
        every tick. Without a client the weekday 09:30-16:00 assumption applies;
        an unreadable calendar counts as closed.
        """
        if day in self._sessions:
            return self._sessions[day]

        if self._client is None:
            session = (
                None if not _local_is_session_day(day) else (_at(day, time(9, 30)), _at(day, _local_close_time(day)))
            )
            self._sessions[day] = session
            return session

        # Cache a failed lookup for the TTL too, or an Alpaca outage turns every
        # 5-minute hook tick into another blocking request.
        now_et = datetime.now(ET)
        if self._session_error_at is not None and (now_et - self._session_error_at).total_seconds() < self._ttl:
            return None

        with self._lock:
            if day in self._sessions:
                return self._sessions[day]
            if self._session_error_at is not None and (now_et - self._session_error_at).total_seconds() < self._ttl:
                return None

            try:
                from alpaca.trading.requests import GetCalendarRequest

                entries = self._call(lambda: self._client.get_calendar(GetCalendarRequest(start=day, end=day)))
            except Exception as exc:
                logger.warning(f"[MarketCalendar] get_calendar failed for {day}; treating as closed: {exc}")
                self._session_error_at = now_et
                return None

            self._session_error_at = None
            session = None
            for entry in entries or []:
                entry_day = getattr(entry, "date", None)
                if isinstance(entry_day, date) and entry_day != day:
                    continue
                open_at = _coerce_et(day, getattr(entry, "open", None))
                close_at = _coerce_et(day, getattr(entry, "close", None))
                if open_at is not None and close_at is not None:
                    session = (open_at, close_at)
                    break

            self._sessions[day] = session
            return session

    def is_session_day(self, day: date) -> bool:
        return self.session_for(day) is not None


_default_calendar = MarketCalendar()


def configure_market_calendar(client: Any = None, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> MarketCalendar:
    """Install the calendar used by the module-level gate (call once at daemon start)."""
    global _default_calendar
    _default_calendar = MarketCalendar(client=client, ttl_seconds=ttl_seconds)
    return _default_calendar


def get_market_calendar() -> MarketCalendar:
    return _default_calendar


def is_market_session_active(now_dt: datetime | None = None) -> bool:
    """Check whether the US regular equity session is running."""
    return _default_calendar.is_open(now_dt)


def seconds_to_next_open(now_dt: datetime | None = None) -> float:
    """Seconds until the next regular session open (holiday-aware when wired)."""
    return _default_calendar.seconds_to_next_open(now_dt)


def is_premarket(now_dt: datetime | None = None) -> bool:
    """Whether it is 04:00-09:30 ET on a weekday."""
    now_et = _as_et(now_dt).astimezone(ET) if now_dt is not None else datetime.now(ET)
    if now_et.weekday() >= 5:
        return False
    premarket_start = now_et.replace(hour=4, minute=0, second=0, microsecond=0)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    return premarket_start <= now_et < market_open
