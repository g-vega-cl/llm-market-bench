"""Unit tests for market_session module."""

import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from execution.market_session import MarketSessionManager


@pytest.fixture(autouse=True)
def reset_session_cache():
    MarketSessionManager._market_status_cache = {
        "is_open": None,
        "fetched_at": None,
        "ttl_seconds": 1800,
    }
    MarketSessionManager._market_status_lock = None
    MarketSessionManager._holidays_cache = {
        "holidays": None,
        "fetched_at": None,
        "ttl_seconds": 86400,
    }
    MarketSessionManager._holidays_lock = None


@pytest.mark.asyncio
async def test_is_market_open_fmp_open():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"isMarketOpen": True}]

    session = MarketSessionManager(fmp_api_key="test_key")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        is_open = await session.is_market_open()
        assert is_open is True


@pytest.mark.asyncio
async def test_is_market_open_weekday_buffer_override():
    # FMP says closed, but time is 9:35 AM ET on a Wednesday
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"isMarketOpen": False}]

    session = MarketSessionManager(fmp_api_key="test_key")
    wed_935am = datetime.datetime(2026, 8, 19, 9, 35, 0, tzinfo=ZoneInfo("America/New_York"))

    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp),
        patch("datetime.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = wed_935am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        is_open = await session.is_market_open()
        assert is_open is True


@pytest.mark.asyncio
async def test_is_market_open_time_fallback_when_no_api_key():
    session = MarketSessionManager(fmp_api_key="")

    # 11:00 AM ET Wednesday -> Open
    wed_11am = datetime.datetime(2026, 8, 19, 11, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    with patch("execution.market_session.datetime.datetime") as mock_dt:
        mock_dt.now.return_value = wed_11am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await session.is_market_open() is True

    # Reset cache
    MarketSessionManager._market_status_cache["fetched_at"] = None

    # 8:00 PM ET Wednesday -> Closed
    wed_8pm = datetime.datetime(2026, 8, 19, 20, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    with patch("execution.market_session.datetime.datetime") as mock_dt:
        mock_dt.now.return_value = wed_8pm
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await session.is_market_open() is False


@pytest.mark.asyncio
async def test_is_market_open_lock_serialization():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"isMarketOpen": True}]

    call_count = 0

    async def slow_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return mock_resp

    session = MarketSessionManager(fmp_api_key="test_key")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=slow_get):
        results = await asyncio.gather(session.is_market_open(), session.is_market_open(), session.is_market_open())
        assert all(results)
        assert call_count == 1


@pytest.mark.asyncio
async def test_get_market_holidays_caching():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"date": "2026-12-25", "name": "Christmas"}]

    session = MarketSessionManager(fmp_api_key="test_key")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp) as mock_get:
        h1 = await session.get_market_holidays()
        h2 = await session.get_market_holidays()
        assert h1 == h2
        assert mock_get.call_count == 1


def test_is_known_us_market_holiday_fallback():
    # New Year's Day
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 1, 1))
    # MLK Day (3rd Mon in Jan 2026 is Jan 19)
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 1, 19))
    # Washington's Birthday (3rd Mon in Feb 2026 is Feb 16)
    assert MarketSessionManager.is_known_us_market_holiday_fallback(datetime.date(2026, 2, 16))
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
async def test_is_trading_day():
    session = MarketSessionManager(fmp_api_key="test_key")

    # Weekend
    assert await session.is_trading_day("2026-09-05") is False
    assert await session.is_trading_day("2026-09-06") is False

    # Holiday from FMP
    mock_holidays = [{"date": "2026-09-07", "isClosed": True}]
    with patch.object(session, "get_market_holidays", new_callable=AsyncMock, return_value=mock_holidays):
        assert await session.is_trading_day("2026-09-07") is False

    # Regular day
    with patch.object(session, "get_market_holidays", new_callable=AsyncMock, return_value=[]):
        assert await session.is_trading_day("2026-09-08") is True


@pytest.mark.asyncio
async def test_is_premarket():
    # Wednesday 8:00 AM ET -> Premarket
    wed_8am = datetime.datetime(2026, 8, 19, 8, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    with patch("execution.market_session.datetime.datetime") as mock_dt:
        mock_dt.now.return_value = wed_8am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await MarketSessionManager.is_premarket() is True

    # Wednesday 10:30 AM ET -> Regular hours (not premarket)
    wed_1030am = datetime.datetime(2026, 8, 19, 10, 30, 0, tzinfo=ZoneInfo("America/New_York"))
    with patch("execution.market_session.datetime.datetime") as mock_dt:
        mock_dt.now.return_value = wed_1030am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await MarketSessionManager.is_premarket() is False

    # Saturday 8:00 AM ET -> Weekend (not premarket)
    sat_8am = datetime.datetime(2026, 8, 22, 8, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    with patch("execution.market_session.datetime.datetime") as mock_dt:
        mock_dt.now.return_value = sat_8am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await MarketSessionManager.is_premarket() is False
