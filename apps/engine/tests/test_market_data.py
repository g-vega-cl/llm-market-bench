"""Unit tests for MarketDataManager caching logic."""

import pytest
import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from execution.market_data import MarketDataManager
from execution.providers.base import TickerData


@pytest.mark.asyncio
async def test_market_data_manager_cache_hit():
    """Test that manager returns data from cache if available and fresh."""
    mock_data = {
        "ticker": "AAPL",
        "price": 150.0,
        "market_cap": 2.5e12,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    with patch("execution.market_data.get_supabase_client") as mock_db:
        mock_client = mock_db.return_value
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_data]
        
        manager = MarketDataManager()
        # Mock provider to ensure it's NOT called
        manager.provider = AsyncMock()
        
        result = await manager.get_quote("AAPL")
        
        assert result is not None
        assert result.ticker == "AAPL"
        assert result.price == 150.0
        assert manager.provider.get_ticker_data.call_count == 0


@pytest.mark.asyncio
async def test_market_data_manager_cache_stale():
    """Test that manager fetches from provider if cache is stale."""
    # 5 hours ago (default TTL is 4)
    stale_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).isoformat()
    mock_cached_data = {
        "ticker": "TSLA",
        "price": 100.0,
        "market_cap": 500e9,
        "fetched_at": stale_time
    }
    
    mock_provider_data = TickerData(
        ticker="TSLA",
        price=200.0,
        market_cap=600e9,
        exists=True
    )
    
    with patch("execution.market_data.get_supabase_client") as mock_db:
        mock_client = mock_db.return_value
        # Cache returns stale data
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_cached_data]
        # Upsert mock
        mock_client.table.return_value.upsert.return_value.execute = MagicMock()
        
        manager = MarketDataManager()
        manager.provider.get_ticker_data = AsyncMock(return_value=mock_provider_data)
        
        result = await manager.get_quote("TSLA")
        
        assert result is not None
        assert result.price == 200.0  # Fresh data
        assert manager.provider.get_ticker_data.call_count == 1


@pytest.mark.asyncio
async def test_market_data_manager_cache_miss():
    """Test that manager fetches and saves if cache is empty."""
    mock_provider_data = TickerData(
        ticker="NVDA",
        price=500.0,
        market_cap=1.2e12,
        exists=True
    )
    
    with patch("execution.market_data.get_supabase_client") as mock_db:
        mock_client = mock_db.return_value
        # Cache returns empty
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        # Upsert mock
        mock_client.table.return_value.upsert.return_value.execute = MagicMock()
        
        manager = MarketDataManager()
        manager.provider.get_ticker_data = AsyncMock(return_value=mock_provider_data)
        
        result = await manager.get_quote("NVDA")
        
        assert result is not None
        assert result.ticker == "NVDA"
        assert manager.provider.get_ticker_data.call_count == 1
        assert mock_client.table.return_value.upsert.call_count == 1
