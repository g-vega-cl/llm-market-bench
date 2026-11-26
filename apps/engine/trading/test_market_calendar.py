"""Hermetic tests for the authoritative US equity session calendar.

Alpaca's /v2/clock knows market holidays, half-day early closes and ad-hoc
closures; weekday + 09:30-16:00 ET arithmetic does not.
"""

from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from trading.market_calendar import MarketCalendar, is_known_us_market_holiday

ET = ZoneInfo("America/New_York")


def _clock(is_open: bool, next_open: datetime | None = None) -> MagicMock:
    clock = MagicMock()
    clock.is_open = is_open
    clock.next_open = next_open
    return clock


def _client(clock: MagicMock | None = None, error: Exception | None = None) -> MagicMock:
    client = MagicMock()
    if error is not None:
        client.get_clock.side_effect = error
    else:
        client.get_clock.return_value = clock
    return client


def test_holiday_is_closed_inside_regular_hours():
    """Thanksgiving 2026-11-26 10:00 ET: weekday math says open, Alpaca says closed."""
    calendar = MarketCalendar(client=_client(_clock(False)))
    assert calendar.is_open(datetime(2026, 11, 26, 10, 0, tzinfo=ET)) is False


def test_half_day_close_is_respected():
    """2026-11-27 is a 13:00 ET early close."""
    calendar = MarketCalendar(client=_client(_clock(False)))
    assert calendar.is_open(datetime(2026, 11, 27, 13, 1, tzinfo=ET)) is False


def test_clock_is_cached_within_ttl():
    client = _client(_clock(True))
    calendar = MarketCalendar(client=client, ttl_seconds=60)
    now = datetime(2026, 11, 27, 10, 0, tzinfo=ET)

    assert calendar.is_open(now) is True
    assert calendar.is_open(now + timedelta(seconds=30)) is True
    assert client.get_clock.call_count == 1


def test_cache_refreshes_after_ttl():
    client = _client(_clock(True))
    calendar = MarketCalendar(client=client, ttl_seconds=60)
    now = datetime(2026, 11, 27, 10, 0, tzinfo=ET)

    calendar.is_open(now)
    calendar.is_open(now + timedelta(seconds=61))
    assert client.get_clock.call_count == 2


def test_fails_closed_when_clock_raises():
    """A client that cannot be read must not fall back to weekday arithmetic."""
    calendar = MarketCalendar(client=_client(error=RuntimeError("boom")))
    # 10:00 ET on a Friday would be open under the local fallback.
    assert calendar.is_open(datetime(2026, 11, 27, 10, 0, tzinfo=ET)) is False


def test_failure_is_cached_within_ttl():
    client = _client(error=RuntimeError("boom"))
    calendar = MarketCalendar(client=client, ttl_seconds=60)
    now = datetime(2026, 11, 27, 10, 0, tzinfo=ET)

    calendar.is_open(now)
    calendar.is_open(now + timedelta(seconds=10))
    assert client.get_clock.call_count == 1


def test_without_client_uses_weekday_and_time():
    calendar = MarketCalendar()

    assert calendar.is_open(datetime(2026, 11, 27, 10, 0, tzinfo=ET)) is True
    assert calendar.is_open(datetime(2026, 11, 27, 8, 0, tzinfo=ET)) is False
    assert calendar.is_open(datetime(2026, 11, 28, 10, 0, tzinfo=ET)) is False


def test_seconds_to_next_open_prefers_clock():
    now = datetime(2026, 11, 26, 10, 0, tzinfo=ET)
    next_open = datetime(2026, 11, 27, 9, 30, tzinfo=ET)
    calendar = MarketCalendar(client=_client(_clock(False, next_open=next_open)))

    assert calendar.seconds_to_next_open(now) == pytest.approx((next_open - now).total_seconds())


def test_seconds_to_next_open_falls_back_without_client():
    now = datetime(2026, 11, 27, 10, 0, tzinfo=ET)  # Friday, session running
    expected_open = datetime(2026, 11, 30, 9, 30, tzinfo=ET)  # Monday 09:30 ET

    calendar = MarketCalendar()
    assert calendar.seconds_to_next_open(now) == pytest.approx((expected_open - now).total_seconds())


# ---------------------------------------------------------------------------
# Day session lookup (/v2/calendar) — holidays, half-days, close-print tail
# ---------------------------------------------------------------------------


def _entry(day, open_time=time(9, 30), close_time=time(16, 0)):
    entry = MagicMock()
    entry.date = day
    entry.open = open_time
    entry.close = close_time
    return entry


def test_session_for_holiday_is_none():
    client = _client()
    client.get_calendar.return_value = []
    calendar = MarketCalendar(client=client)

    assert calendar.session_for(date(2026, 11, 26)) is None


def test_session_for_trading_day_returns_et_bounds():
    day = date(2026, 11, 25)
    client = _client()
    client.get_calendar.return_value = [_entry(day)]
    calendar = MarketCalendar(client=client)

    session = calendar.session_for(day)
    assert session == (datetime(2026, 11, 25, 9, 30, tzinfo=ET), datetime(2026, 11, 25, 16, 0, tzinfo=ET))


def test_session_for_half_day_reports_early_close():
    day = date(2026, 11, 27)
    client = _client()
    client.get_calendar.return_value = [_entry(day, close_time=time(13, 0))]
    calendar = MarketCalendar(client=client)

    session = calendar.session_for(day)
    assert session is not None
    assert session[1] == datetime(2026, 11, 27, 13, 0, tzinfo=ET)


def test_session_for_is_cached_per_day():
    day = date(2026, 11, 25)
    client = _client()
    client.get_calendar.return_value = [_entry(day)]
    calendar = MarketCalendar(client=client)

    calendar.session_for(day)
    calendar.session_for(day)
    assert client.get_calendar.call_count == 1


def test_session_for_fails_closed_when_calendar_raises():
    client = _client()
    client.get_calendar.side_effect = RuntimeError("boom")
    calendar = MarketCalendar(client=client)

    assert calendar.session_for(date(2026, 11, 27)) is None


def test_session_for_without_client_uses_weekday_bounds():
    calendar = MarketCalendar()

    # 2026-11-27 is the day after Thanksgiving: a scheduled 13:00 early close.
    friday = calendar.session_for(date(2026, 11, 27))
    assert friday == (datetime(2026, 11, 27, 9, 30, tzinfo=ET), datetime(2026, 11, 27, 13, 0, tzinfo=ET))
    # A plain Friday keeps the full session.
    plain = calendar.session_for(date(2026, 11, 20))
    assert plain == (datetime(2026, 11, 20, 9, 30, tzinfo=ET), datetime(2026, 11, 20, 16, 0, tzinfo=ET))
    assert calendar.session_for(date(2026, 11, 28)) is None  # Saturday


# ---------------------------------------------------------------------------
# Hardening: cache staleness, naive inputs, timeouts, failure caching
# ---------------------------------------------------------------------------


def test_cached_open_clock_cannot_outlive_its_own_close():
    """A clock read at 15:59 must not report open at 16:00:20 from cache."""
    clock = _clock(True)
    clock.next_close = datetime(2026, 11, 25, 16, 0, tzinfo=ET)
    calendar = MarketCalendar(client=_client(clock), ttl_seconds=60)

    calendar.is_open(datetime(2026, 11, 25, 15, 59, 30, tzinfo=ET))
    assert calendar.is_open(datetime(2026, 11, 25, 16, 0, 20, tzinfo=ET)) is False


def test_naive_datetime_is_read_as_eastern():
    """A naive input must not raise on the cache arithmetic."""
    clock = _clock(True)
    clock.next_close = datetime(2026, 11, 25, 16, 0, tzinfo=ET)
    calendar = MarketCalendar(client=_client(clock))

    assert calendar.is_open(datetime(2026, 11, 25, 10, 0)) is True


def test_hung_clock_call_times_out_closed():
    """alpaca-py sets no requests timeout; the gate must not block on a hang."""
    import time as _time

    client = MagicMock()
    client.get_clock.side_effect = lambda: (_time.sleep(0.3), _clock(True))[1]
    calendar = MarketCalendar(client=client, call_timeout_seconds=0.05)

    started = _time.perf_counter()
    assert calendar.is_open(datetime(2026, 11, 25, 10, 0, tzinfo=ET)) is False
    assert _time.perf_counter() - started < 0.25


def test_timed_out_worker_is_replaced_not_starved():
    """A hung call must not occupy the only worker for every later caller."""
    import time as _time

    from trading import market_calendar as module

    hung_client = MagicMock()
    hung_client.get_clock.side_effect = lambda: (_time.sleep(0.4), _clock(True))[1]
    hung = MarketCalendar(client=hung_client, call_timeout_seconds=0.05)
    assert hung.is_open(datetime(2026, 11, 25, 10, 0, tzinfo=ET)) is False

    healthy_clock = _clock(True)
    healthy_clock.next_close = datetime(2026, 11, 25, 16, 0, tzinfo=ET)
    healthy = MarketCalendar(client=_client(healthy_clock), call_timeout_seconds=0.05)

    started = _time.perf_counter()
    assert healthy.is_open(datetime(2026, 11, 25, 10, 0, tzinfo=ET)) is True
    assert _time.perf_counter() - started < 0.2
    assert module._CALL_EXECUTOR is not None


def test_calendar_failure_is_cached_within_ttl():
    client = _client()
    client.get_calendar.side_effect = RuntimeError("boom")
    calendar = MarketCalendar(client=client, ttl_seconds=60)

    calendar.session_for(date(2026, 11, 25))
    calendar.session_for(date(2026, 11, 25))
    assert client.get_calendar.call_count == 1


def test_session_entry_for_another_day_is_ignored():
    client = _client()
    client.get_calendar.return_value = [_entry(date(2026, 11, 24))]
    calendar = MarketCalendar(client=client)

    assert calendar.session_for(date(2026, 11, 25)) is None


def test_dec_31_is_a_session_when_next_new_year_is_saturday():
    """NYSE trades 2027-12-31 (Jan 1 2028 is a Saturday); only Jan 1 and Jan 2 are closed."""
    calendar = MarketCalendar()

    assert not is_known_us_market_holiday(date(2027, 12, 31))
    session = calendar.session_for(date(2027, 12, 31))
    assert session is not None
    assert session[0].strftime("%H:%M") == "09:30"
    assert session[1].strftime("%H:%M") == "16:00"
