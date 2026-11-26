"""Unit tests for the market_session adapter (delegates to trading.market_calendar)."""

import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from execution.market_session import MarketSessionManager
from trading.market_calendar import configure_market_calendar

ET = ZoneInfo("America/New_York")


@pytest.fixture(autouse=True)
def reset_calendar():
    yield
    configure_market_calendar(None)


@pytest.mark.asyncio
async def test_is_market_open_delegates_to_configured_calendar():
    """The manager no longer queries FMP; it reports the calendar's answer."""
    client = MagicMock()
    client.get_clock.return_value.is_open = True
    configure_market_calendar(client)

    session = MarketSessionManager()
    assert await session.is_market_open() is True

    client.get_clock.return_value.is_open = False
    configure_market_calendar(client)
    assert await MarketSessionManager().is_market_open() is False


@pytest.mark.asyncio
async def test_is_market_open_excludes_holidays_without_a_client():
    """Offline path: 10:15 ET on Thanksgiving is closed; the same hour on a Wednesday is open."""
    configure_market_calendar(None)

    with patch("trading.market_calendar.datetime") as mock_dt:
        mock_dt.now.return_value = datetime.datetime(2026, 11, 26, 10, 15, tzinfo=ET)
        assert await MarketSessionManager().is_market_open() is False

    with patch("trading.market_calendar.datetime") as mock_dt:
        mock_dt.now.return_value = datetime.datetime(2026, 11, 25, 10, 15, tzinfo=ET)
        assert await MarketSessionManager().is_market_open() is True


# ---------------------------------------------------------------------------
# Offline rules (kept as the fallback when no trading client is wired)
# ---------------------------------------------------------------------------


def test_is_known_us_market_holiday_fallback():
    # New Year's Day
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 1, 1))
    # MLK Day (3rd Mon in Jan 2026 is Jan 19)
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 1, 19))
    # Washington's Birthday (3rd Mon in Feb 2026 is Feb 16)
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 2, 16))
    # Good Friday 2026-04-03
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 4, 3))
    # Memorial Day (Last Mon in May 2026 is May 25)
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 5, 25))
    # Juneteenth 2026-06-19
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 6, 19))
    # July 4 (observed July 3 if Sat - July 4 2026 is Sat, July 3 is Fri)
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 7, 3))
    # Labor Day (1st Mon in Sep 2026 is Sep 7)
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 9, 7))
    # Thanksgiving (4th Thu in Nov 2026 is Nov 26)
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 11, 26))
    # Christmas 2026-12-25
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 12, 25))
    # Regular trading day
    assert not MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 9, 8))


@pytest.mark.asyncio
async def test_is_trading_day_uses_calendar_rules():
    configure_market_calendar(None)
    session = MarketSessionManager()

    assert await session.is_trading_day("2026-09-05") is False  # Saturday
    assert await session.is_trading_day("2026-09-06") is False  # Sunday
    assert await session.is_trading_day("2026-11-26") is False  # Thanksgiving
    assert await session.is_trading_day("2026-09-08") is True  # regular Tuesday


@pytest.mark.asyncio
async def test_get_market_holidays_derives_non_session_weekdays():
    """Holidays come from the calendar now, not an FMP fetch."""
    configure_market_calendar(None)

    holidays = await MarketSessionManager().get_market_holidays()
    dates = {h["date"] for h in holidays}

    assert "2026-12-25" in dates  # Christmas
    assert all(datetime.date.fromisoformat(d).weekday() < 5 for d in dates)


@pytest.mark.asyncio
async def test_is_premarket():
    # Wednesday 8:00 AM ET -> Premarket
    wed_8am = datetime.datetime(2026, 8, 19, 8, 0, 0, tzinfo=ET)
    with patch("execution.market_session.datetime.datetime") as mock_dt:
        mock_dt.now.return_value = wed_8am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await MarketSessionManager.is_premarket() is True

    # Wednesday 10:30 AM ET -> Regular hours (not premarket)
    wed_1030am = datetime.datetime(2026, 8, 19, 10, 30, 0, tzinfo=ET)
    with patch("execution.market_session.datetime.datetime") as mock_dt:
        mock_dt.now.return_value = wed_1030am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await MarketSessionManager.is_premarket() is False

    # Saturday 8:00 AM ET -> Weekend (not premarket)
    sat_8am = datetime.datetime(2026, 8, 22, 8, 0, 0, tzinfo=ET)
    with patch("execution.market_session.datetime.datetime") as mock_dt:
        mock_dt.now.return_value = sat_8am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await MarketSessionManager.is_premarket() is False
