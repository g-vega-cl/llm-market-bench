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



@pytest.mark.asyncio
async def test_get_history_cache_hit_includes_volume():
    """Cache-hit path must pass volume through to callers.

    Fails before fix: SELECT omits 'volume' and the return dict never sets it,
    so compute_volume_context receives None values and returns
    'insufficient volume data' even when the DB has volume stored.
    """
    import datetime

    mock_supabase = MagicMock()
    today_date = datetime.datetime.now(datetime.UTC).date()

    mock_rows = [
        {
            "price": float(100 + i),
            "open": float(100 + i),
            "high": float(101 + i),
            "low": float(99 + i),
            "close": float(100 + i),
            "volume": 10_000_000 + i * 1_000,
            "fetched_at": f"{(today_date - datetime.timedelta(days=i + 1)).isoformat()}T10:00:00",
        }
        for i in range(8)
    ]
    mock_res = MagicMock()
    mock_res.data = mock_rows
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()

    with (
        patch("execution.market_data.get_supabase_client", return_value=mock_supabase),
        patch("execution.market_data.get_financial_provider", return_value=mock_provider),
    ):
        manager = MarketDataManager()
        history = await manager.get_history("AAPL", days=10)

    assert len(history) == 8
    # Every entry must carry a non-None volume
    volumes = [h.get("volume") for h in history]
    assert all(v is not None for v in volumes), f"Expected all volumes to be set, got: {volumes}"
    assert volumes[0] == 10_000_000  # first row


@pytest.mark.asyncio
async def test_get_history_save_persists_volume():
    """Provider-fetch path must write volume into the price_history upsert payload.

    Fails before fix: the payload builder loop never adds a 'volume' key,
    so volume is silently dropped from the DB and future cache hits lack it.
    """
    mock_supabase = MagicMock()
    mock_res = MagicMock()
    mock_res.data = []  # force provider fetch

    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_res

    mock_provider = AsyncMock()
    mock_provider.provider_name = "fmp"
    mock_provider.get_history.return_value = [
        {
            "price": 150.0,
            "open": 148.0,
            "high": 152.0,
            "low": 147.0,
            "close": 150.0,
            "volume": 25_000_000,
            "fetched_at": "2026-09-23",
        },
        {
            "price": 151.0,
            "open": 150.0,
            "high": 153.0,
            "low": 149.0,
            "close": 151.0,
            "volume": 18_000_000,
            "fetched_at": "2026-09-22",
        },
    ]

    with (
        patch("execution.market_data.get_supabase_client", return_value=mock_supabase),
        patch("execution.market_data.get_financial_provider", return_value=mock_provider),
    ):
        manager = MarketDataManager()
        history = await manager.get_history("NVDA", days=14)

    assert len(history) == 2

    # Inspect what was upserted
    upsert_call = mock_supabase.table.return_value.upsert
    upsert_call.assert_called_once()
    payloads = upsert_call.call_args[0][0]
    assert len(payloads) == 2

    volumes_in_db = [p.get("volume") for p in payloads]
    assert volumes_in_db[0] == 25_000_000, f"Expected volume 25_000_000 in upsert payload, got {volumes_in_db[0]}"
    assert volumes_in_db[1] == 18_000_000, f"Expected volume 18_000_000 in upsert payload, got {volumes_in_db[1]}"
