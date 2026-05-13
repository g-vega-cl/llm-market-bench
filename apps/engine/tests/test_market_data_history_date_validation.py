"""
Tests for date-range validation in get_history to ensure cached data
represents true historical EOD data, not same-day realtime ticks.

Bug: get_history() returns today's intraday ticks from price_history table
instead of fetching actual historical EOD data when requesting historical prices.
"""
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.market_data import MarketDataManager


@pytest.fixture
def mock_today():
    """Fixture to provide current date in UTC."""
    return datetime.datetime.now(datetime.UTC).date().isoformat()


@pytest.mark.asyncio
async def test_get_history_rejects_same_day_cache(mock_today):
    """Cache with 20 rows all from today should NOT be used (cache miss).

    This is the core bug: update_prices.py runs every 30 mins and populates
    price_history with same-day ticks. When an LLM requests 7 days of history,
    get_history() incorrectly returns today's ticks instead of fetching from FMP.
    """
    mock_supabase = MagicMock()

    mock_res = MagicMock()
    mock_res.data = [
        {"price": 170.02, "fetched_at": f"{mock_today}T19:59:24.992074+00:00"},
        {"price": 170.03, "fetched_at": f"{mock_today}T19:59:22.132068+00:00"},
        {"price": 169.79, "fetched_at": f"{mock_today}T19:58:48.655156+00:00"},
        {"price": 169.78, "fetched_at": f"{mock_today}T19:58:46.152386+00:00"},
        {"price": 169.82, "fetched_at": f"{mock_today}T19:58:05.544012+00:00"},
        {"price": 170.19, "fetched_at": f"{mock_today}T19:54:18.656045+00:00"},
        {"price": 170.21, "fetched_at": f"{mock_today}T19:54:09.319782+00:00"},
    ]

    mock_query = mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    mock_query.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()
    mock_provider.get_history.return_value = [
        {"price": 172.50, "fetched_at": "2026-04-14"},
        {"price": 171.80, "fetched_at": "2026-04-13"},
        {"price": 171.20, "fetched_at": "2026-04-10"},
    ]

    with patch("execution.market_data.get_supabase_client", return_value=mock_supabase):
        with patch("execution.market_data.get_financial_provider", return_value=mock_provider):
            manager = MarketDataManager()
            history = await manager.get_history("ORCL", days=7)

    mock_provider.get_history.assert_called_once_with("ORCL", 7)
    assert len(history) == 3
    assert history[0]["price"] == 172.50


@pytest.mark.asyncio
async def test_get_history_accepts_multi_day_cache():
    """Cache spanning multiple distinct past dates should be used (cache hit)."""
    mock_supabase = MagicMock()
    mock_res = MagicMock()
    mock_res.data = [
        {"price": 172.50, "fetched_at": "2026-04-14T16:00:00+00:00"},
        {"price": 171.80, "fetched_at": "2026-04-13T16:00:00+00:00"},
        {"price": 171.20, "fetched_at": "2026-04-10T16:00:00+00:00"},
        {"price": 170.50, "fetched_at": "2026-04-09T16:00:00+00:00"},
        {"price": 169.90, "fetched_at": "2026-04-08T16:00:00+00:00"},
        {"price": 169.10, "fetched_at": "2026-04-07T16:00:00+00:00"},
        {"price": 168.30, "fetched_at": "2026-04-04T16:00:00+00:00"},
    ]

    mock_query = mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    mock_query.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()

    with patch("execution.market_data.get_supabase_client", return_value=mock_supabase):
        with patch("execution.market_data.get_financial_provider", return_value=mock_provider):
            manager = MarketDataManager()
            history = await manager.get_history("ORCL", days=7)

    mock_provider.get_history.assert_not_called()
    assert len(history) == 7


@pytest.mark.asyncio
async def test_get_history_requires_minimum_date_span():
    """When requesting N days, cached data must include at least one date older than today."""
    mock_supabase = MagicMock()

    today = "2026-04-15"
    yesterday = "2026-04-14"
    mock_res = MagicMock()
    mock_res.data = [
        {"price": 172.50, "fetched_at": f"{today}T16:00:00+00:00"},
        {"price": 172.00, "fetched_at": f"{today}T12:00:00+00:00"},
        {"price": 171.50, "fetched_at": f"{today}T08:00:00+00:00"},
        {"price": 171.00, "fetched_at": f"{yesterday}T16:00:00+00:00"},
        {"price": 170.50, "fetched_at": f"{yesterday}T12:00:00+00:00"},
    ]

    mock_query = mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    mock_query.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()
    mock_provider.get_history.return_value = [
        {"price": 172.50, "fetched_at": "2026-04-14"},
        {"price": 171.80, "fetched_at": "2026-04-13"},
        {"price": 171.20, "fetched_at": "2026-04-10"},
    ]

    with patch("execution.market_data.get_supabase_client", return_value=mock_supabase):
        with patch("execution.market_data.get_financial_provider", return_value=mock_provider):
            manager = MarketDataManager()
            history = await manager.get_history("ORCL", days=7)

    mock_provider.get_history.assert_called_once()


@pytest.mark.asyncio
async def test_get_history_validates_distinct_trading_days():
    """Cache must span at least half of requested trading days."""
    mock_supabase = MagicMock()

    today = "2026-04-15"
    mock_res = MagicMock()
    mock_res.data = [
        {"price": 172.50, "fetched_at": f"{today}T16:00:00+00:00"},
        {"price": 172.00, "fetched_at": f"{today}T14:00:00+00:00"},
        {"price": 171.50, "fetched_at": f"{today}T12:00:00+00:00"},
        {"price": 171.00, "fetched_at": f"{today}T10:00:00+00:00"},
    ]

    mock_query = mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    mock_query.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()
    mock_provider.get_history.return_value = [
        {"price": 172.50, "fetched_at": "2026-04-14"},
    ]

    with patch("execution.market_data.get_supabase_client", return_value=mock_supabase):
        with patch("execution.market_data.get_financial_provider", return_value=mock_provider):
            manager = MarketDataManager()
            history = await manager.get_history("ORCL", days=10)

    mock_provider.get_history.assert_called_once()


@pytest.mark.asyncio
async def test_get_history_mixed_today_and_old_data_still_fetches():
    """Cache with mostly today's data should not be used even if some old rows exist."""
    mock_supabase = MagicMock()

    old_date = "2026-04-10"
    mock_res = MagicMock()
    mock_res.data = [
        {"price": 172.50, "fetched_at": "2026-04-15T19:59:24+00:00"},
        {"price": 172.00, "fetched_at": "2026-04-15T19:58:22+00:00"},
        {"price": 171.50, "fetched_at": "2026-04-15T19:57:48+00:00"},
        {"price": 171.00, "fetched_at": f"{old_date}T16:00:00+00:00"},
        {"price": 170.50, "fetched_at": f"{old_date}T16:00:00+00:00"},
    ]

    mock_query = mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    mock_query.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()
    mock_provider.get_history.return_value = []

    with patch("execution.market_data.get_supabase_client", return_value=mock_supabase):
        with patch("execution.market_data.get_financial_provider", return_value=mock_provider):
            manager = MarketDataManager()
            history = await manager.get_history("ORCL", days=7)

    mock_provider.get_history.assert_called_once()


@pytest.mark.asyncio
async def test_get_history_pure_historical_cache_works():
    """Cache with only historical data (no today) should still be used."""
    mock_supabase = MagicMock()
    mock_res = MagicMock()
    mock_res.data = [
        {"price": 172.50, "fetched_at": "2026-04-14T16:00:00+00:00"},
        {"price": 172.00, "fetched_at": "2026-04-11T16:00:00+00:00"},
        {"price": 171.50, "fetched_at": "2026-04-10T16:00:00+00:00"},
        {"price": 171.00, "fetched_at": "2026-04-09T16:00:00+00:00"},
        {"price": 170.50, "fetched_at": "2026-04-08T16:00:00+00:00"},
    ]

    mock_query = mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    mock_query.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()

    with patch("execution.market_data.get_supabase_client", return_value=mock_supabase):
        with patch("execution.market_data.get_financial_provider", return_value=mock_provider):
            manager = MarketDataManager()
            history = await manager.get_history("ORCL", days=7)

    mock_provider.get_history.assert_not_called()
    assert len(history) == 5


@pytest.mark.asyncio
async def test_get_history_rejects_single_date_cache():
    """Cache with only 1 distinct historical date should trigger a re-fetch.

    This was the bug: a single-date cache (e.g., all rows from 2026-04-24)
    was incorrectly accepted as valid, freezing price history forever.
    """
    mock_supabase = MagicMock()
    mock_res = MagicMock()
    mock_res.data = [
        {"price": 172.50, "fetched_at": "2026-04-24T16:00:00+00:00"},
        {"price": 172.00, "fetched_at": "2026-04-24T15:00:00+00:00"},
        {"price": 171.50, "fetched_at": "2026-04-24T14:00:00+00:00"},
        {"price": 171.00, "fetched_at": "2026-04-24T13:00:00+00:00"},
        {"price": 170.50, "fetched_at": "2026-04-24T12:00:00+00:00"},
        {"price": 169.90, "fetched_at": "2026-04-24T11:00:00+00:00"},
        {"price": 169.10, "fetched_at": "2026-04-24T10:00:00+00:00"},
    ]

    mock_query = mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    mock_query.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()
    mock_provider.get_history.return_value = [
        {"price": 175.00, "fetched_at": "2026-05-04"},
        {"price": 174.50, "fetched_at": "2026-05-03"},
        {"price": 173.00, "fetched_at": "2026-05-02"},
    ]

    with patch("execution.market_data.get_supabase_client", return_value=mock_supabase):
        with patch("execution.market_data.get_financial_provider", return_value=mock_provider):
            manager = MarketDataManager()
            history = await manager.get_history("MSFT", days=7)

    mock_provider.get_history.assert_called_once_with("MSFT", 7)
    assert len(history) == 3
