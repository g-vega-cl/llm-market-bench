from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.market_data import MarketDataManager
from execution.providers.yfinance import YFinanceProvider


@pytest.mark.asyncio
async def test_market_data_manager_get_history_cache_hit():
    """Test that MarketDataManager uses local DB if enough data is found."""
    mock_supabase = MagicMock()
    mock_res = MagicMock()
    mock_res.data = [
        {"price": 100.0, "volume": 10000000, "fetched_at": "2026-02-01T10:00:00"},
        {"price": 101.0, "volume": 10000000, "fetched_at": "2026-02-02T10:00:00"},
        {"price": 102.0, "volume": 10000000, "fetched_at": "2026-02-03T10:00:00"},
        {"price": 103.0, "volume": 10000000, "fetched_at": "2026-02-04T10:00:00"},
        {"price": 104.0, "volume": 10000000, "fetched_at": "2026-02-05T10:00:00"},
        {"price": 105.0, "volume": 10000000, "fetched_at": "2026-02-06T10:00:00"},
        {"price": 106.0, "volume": 10000000, "fetched_at": "2026-02-07T10:00:00"},
        {"price": 107.0, "volume": 10000000, "fetched_at": "2026-02-08T10:00:00"},
    ]
    
    # Supabase chaining mock
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_res
    
    mock_provider = AsyncMock()
    
    with patch("execution.market_data.get_supabase_client", return_value=mock_supabase):
        with patch("execution.market_data.get_financial_provider", return_value=mock_provider):
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
    mock_res.data = [] # No data locally
    
    mock_query = mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    mock_query.return_value.execute.return_value = mock_res
    
    mock_provider = AsyncMock()
    mock_provider.get_history.return_value = [
        {"price": 150.0, "volume": 10000000, "fetched_at": "2026-02-01T10:00:00"},
        {"price": 151.0, "volume": 10000000, "fetched_at": "2026-02-02T10:00:00"}
    ]
    
    with patch("execution.market_data.get_supabase_client", return_value=mock_supabase):
        with patch("execution.market_data.get_financial_provider", return_value=mock_provider):
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
async def test_yfinance_provider_get_history():
    """Test YFinanceProvider history fetching logic."""
    provider = YFinanceProvider()
    
    mock_ticker = MagicMock()
    mock_hist = MagicMock()
    mock_hist.empty = False
    
    import datetime

    import pandas as pd
    
    data = {
        "Close": [100.0, 101.0, 102.0]
    }
    index = pd.to_datetime([
        datetime.datetime(2026, 2, 1),
        datetime.datetime(2026, 2, 2),
        datetime.datetime(2026, 2, 3)
    ])
    mock_hist = pd.DataFrame(data, index=index)
    mock_ticker.history.return_value = mock_hist
    
    with patch("yfinance.Ticker", return_value=mock_ticker):
        # YFinance is sync, run in executor mock
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            # Mock run_in_executor to just call the function for Ticker info
            async def mock_run_in_executor(executor, func, *args):
                return func(*args)
            mock_loop_instance.run_in_executor = mock_run_in_executor
            mock_loop.return_value = mock_loop_instance
            
            history = await provider.get_history("MSFT", days=3)
            
    assert len(history) == 3
    # Our provider reverses to latest-first
    assert history[0]["price"] == 102.0
    assert "2026-02-03" in history[0]["fetched_at"]
