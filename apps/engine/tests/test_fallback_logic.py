"""Unit tests for MarketDataManager single-provider retry behavior."""

import pytest
import math
from unittest.mock import MagicMock, AsyncMock, patch
from execution.market_data import MarketDataManager
from execution.providers.base import TickerData


@pytest.mark.asyncio
async def test_market_data_manager_retries_single_provider():
    """Test that manager retries the configured provider before falling back to history."""
    
    mock_ticker = "AAPL"
    
    provider = AsyncMock()
    provider.provider_name = "primary_mock"
    provider.get_ticker_data.return_value = TickerData(
        ticker=mock_ticker,
        price=150.0,
        market_cap=2.5e12,
        exists=True
    )
    
    with patch("execution.market_data.get_supabase_client") as mock_db, \
         patch("execution.market_data.get_financial_provider") as mock_factory:
        
        # Mock DB setup to avoid real calls
        mock_client = mock_db.return_value
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_client.table.return_value.upsert.return_value.execute = MagicMock()
        mock_client.table.return_value.insert.return_value.execute = MagicMock()

        # Config override via patch (simulating config.py state)
        with patch("core.config.FINANCIAL_PROVIDER", "primary_mock"), \
             patch("core.config.MARKET_DATA_RETRIES", 3):
            
            mock_factory.return_value = provider
            
            manager = MarketDataManager()
            assert len(manager.providers) == 1
            result = await manager.get_quote(mock_ticker)
            
            assert result is not None
            assert result.price == 150.0
            assert provider.get_ticker_data.call_count == 1


@pytest.mark.asyncio
async def test_market_data_manager_honors_retries():
    """Test that manager retries the configured number of times per provider."""
    
    mock_ticker = "FAIL"
    retries = 3
    
    # Mock a provider that always fails
    provider = AsyncMock()
    provider.provider_name = "failing_mock"
    provider.get_ticker_data.return_value = None
    
    with patch("execution.market_data.get_supabase_client") as mock_db, \
         patch("execution.market_data.get_financial_provider") as mock_factory:
        
        # Mock DB setup - make sure execute returns an empty list for data
        mock_client = mock_db.return_value
        mock_execute = MagicMock()
        mock_execute.data = []
        
        # Configure the chain to return the mock_execute
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_execute
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_execute

        # Config override - only one configured provider should be initialized
        with patch("core.config.FINANCIAL_PROVIDER", "failing_mock"), \
             patch("core.config.MARKET_DATA_RETRIES", retries):
            
            mock_factory.return_value = provider
            
            manager = MarketDataManager()
            assert len(manager.providers) == 1
            # Suppress sleep for speed
            with patch("asyncio.sleep", AsyncMock()):
                result = await manager.get_quote(mock_ticker)
            
            assert result is None
            # Provider should be tried exactly 'retries' times since it's the only configured source
            assert provider.get_ticker_data.call_count == retries


@pytest.mark.asyncio
async def test_market_data_manager_initializes_single_provider():
    """Test that manager only initializes the configured provider."""
    
    with patch("execution.market_data.get_supabase_client"), \
         patch("execution.market_data.get_financial_provider") as mock_factory:
        
        with patch("core.config.FINANCIAL_PROVIDER", "same"):
            
            manager = MarketDataManager()
            
            assert len(manager.providers) == 1
            assert mock_factory.call_count == 1
