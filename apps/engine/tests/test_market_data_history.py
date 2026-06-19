from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.market_data import MarketDataManager


@pytest.mark.asyncio
async def test_market_data_manager_get_history_cache_hit():
    """Test that MarketDataManager uses local DB if enough data is found."""
    mock_supabase = MagicMock()
    import datetime

    today_date = datetime.datetime.now(datetime.UTC).date()
    mock_res = MagicMock()
    mock_res.data = [
        {
            "price": 100.0,
            "volume": 10000000,
            "fetched_at": f"{(today_date - datetime.timedelta(days=8)).isoformat()}T10:00:00",
        },
        {
            "price": 101.0,
            "volume": 10000000,
            "fetched_at": f"{(today_date - datetime.timedelta(days=7)).isoformat()}T10:00:00",
        },
        {
            "price": 102.0,
            "volume": 10000000,
            "fetched_at": f"{(today_date - datetime.timedelta(days=6)).isoformat()}T10:00:00",
        },
        {
            "price": 103.0,
            "volume": 10000000,
            "fetched_at": f"{(today_date - datetime.timedelta(days=5)).isoformat()}T10:00:00",
        },
        {
            "price": 104.0,
            "volume": 10000000,
            "fetched_at": f"{(today_date - datetime.timedelta(days=4)).isoformat()}T10:00:00",
        },
        {
            "price": 105.0,
            "volume": 10000000,
            "fetched_at": f"{(today_date - datetime.timedelta(days=3)).isoformat()}T10:00:00",
        },
        {
            "price": 106.0,
            "volume": 10000000,
            "fetched_at": f"{(today_date - datetime.timedelta(days=2)).isoformat()}T10:00:00",
        },
        {
            "price": 107.0,
            "volume": 10000000,
            "fetched_at": f"{(today_date - datetime.timedelta(days=1)).isoformat()}T10:00:00",
        },
    ]

    # Supabase chaining mock
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()

    with (
        patch("execution.market_data.get_supabase_client", return_value=mock_supabase),
        patch("execution.market_data.get_financial_provider", return_value=mock_provider),
    ):
        manager = MarketDataManager()
        # Request 10 days, we have 8 (80% which is >= 70% threshold)
        history = await manager.get_history("AAPL", days=10)

    assert len(history) == 8
    assert history[0]["price"] == 100.0
    mock_provider.get_history.assert_not_called()


@pytest.mark.asyncio
async def test_market_data_manager_get_history_fallback_batch_upsert():
    """Test that MarketDataManager falls back to provider and performs batch upsert."""
    mock_supabase = MagicMock()
    mock_res = MagicMock()
    mock_res.data = []  # No data locally

    mock_query = mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    mock_query.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()
    mock_provider.get_history.return_value = [
        {"price": 150.0, "volume": 10000000, "fetched_at": "2026-02-01T10:00:00"},
        {"price": 151.0, "volume": 10000000, "fetched_at": "2026-02-02T10:00:00"},
    ]

    with (
        patch("execution.market_data.get_supabase_client", return_value=mock_supabase),
        patch("execution.market_data.get_financial_provider", return_value=mock_provider),
    ):
        manager = MarketDataManager()
        history = await manager.get_history("NEW_STOCK", days=14)

    assert len(history) == 2
    mock_provider.get_history.assert_called_once_with("NEW_STOCK", 14)

    # Verify batch upsert was called
    mock_upsert = mock_supabase.table.return_value.upsert
    mock_upsert.assert_called_once()
    args, kwargs = mock_upsert.call_args
    assert isinstance(args[0], list)
    assert len(args[0]) == 2
    assert args[0][0]["ticker"] == "NEW_STOCK"
    assert args[0][0]["price"] == 150.0


# Finished history tests
