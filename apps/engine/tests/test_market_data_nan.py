import pytest
import math
from unittest.mock import MagicMock, patch
from execution.market_data import MarketDataManager
from execution.providers.base import TickerData

@pytest.fixture
def mock_supabase():
    with patch("execution.market_data.get_supabase_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client

@pytest.mark.asyncio
async def test_save_to_cache_skips_nan(mock_supabase):
    manager = MarketDataManager()
    
    # Test case 1: Price is NaN
    nan_data = TickerData(
        ticker="AAPL",
        price=float('nan'),
        market_cap=3000000000000.0,
        exists=True
    )
    
    manager._save_to_cache(nan_data)
    
    # Verify that supabase client was NOT called for upsert or insert
    mock_supabase.table.assert_not_called()

    # Test case 2: Market cap is NaN
    nan_data_2 = TickerData(
        ticker="GOOGL",
        price=150.0,
        market_cap=float('nan'),
        exists=True
    )
    
    manager._save_to_cache(nan_data_2)
    mock_supabase.table.assert_not_called()

    # Test case 3: Valid data
    valid_data = TickerData(
        ticker="MSFT",
        price=400.0,
        market_cap=3000000000000.0,
        exists=True
    )
    
    manager._save_to_cache(valid_data)
    
    # Verify that supabase client WAS called (only for market_data_cache now)
    assert mock_supabase.table.call_count == 1
    mock_supabase.table.assert_called_once_with("market_data_cache")
