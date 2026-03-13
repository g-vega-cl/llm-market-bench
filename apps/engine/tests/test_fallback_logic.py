"""Unit tests for MarketDataManager triple fallback and retry logic."""

import pytest
import math
from unittest.mock import MagicMock, AsyncMock, patch
from execution.market_data import MarketDataManager
from execution.providers.base import TickerData


@pytest.mark.asyncio
async def test_market_data_manager_triple_fallback():
    """Test that manager falls back through primary, secondary, and tertiary providers."""
    
    mock_ticker = "AAPL"
    
    # Mock three providers
    primary = AsyncMock()
    primary.provider_name = "primary_mock"
    primary.get_ticker_data.return_value = None # Fails
    
    secondary = AsyncMock()
    secondary.provider_name = "secondary_mock"
    secondary.get_ticker_data.return_value = None # Fails
    
    tertiary = AsyncMock()
    tertiary.provider_name = "tertiary_mock"
    tertiary.get_ticker_data.return_value = TickerData(
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
             patch("core.config.FALLBACK_FINANCIAL_PROVIDER", "secondary_mock"), \
             patch("core.config.SECOND_FALLBACK_FINANCIAL_PROVIDER", "tertiary_mock"), \
             patch("core.config.MARKET_DATA_RETRIES", 1): # Speed up test
            
            # Setup factory to return our mocks
            def factory_side_effect(name):
                if name == "primary_mock": return primary
                if name == "secondary_mock": return secondary
                if name == "tertiary_mock": return tertiary
                return MagicMock()
            
            mock_factory.side_effect = factory_side_effect
            
            manager = MarketDataManager()
            result = await manager.get_quote(mock_ticker)
            
            assert result is not None
            assert result.price == 150.0
            assert primary.get_ticker_data.call_count == 1
            assert secondary.get_ticker_data.call_count == 1
            assert tertiary.get_ticker_data.call_count == 1


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

        # Config override - use SAME name to test de-duplication to 1 provider
        with patch("core.config.FINANCIAL_PROVIDER", "failing_mock"), \
             patch("core.config.FALLBACK_FINANCIAL_PROVIDER", "failing_mock"), \
             patch("core.config.SECOND_FALLBACK_FINANCIAL_PROVIDER", "failing_mock"), \
             patch("core.config.MARKET_DATA_RETRIES", retries):
            
            mock_factory.return_value = provider
            
            manager = MarketDataManager()
            # Suppress sleep for speed
            with patch("asyncio.sleep", AsyncMock()):
                result = await manager.get_quote(mock_ticker)
            
            assert result is None
            # Provider should be tried exactly 'retries' times since it's the only one in the chain
            assert provider.get_ticker_data.call_count == retries


@pytest.mark.asyncio
async def test_market_data_manager_deduplicates_providers():
    """Test that manager doesn't initialize duplicate providers in the chain."""
    
    with patch("execution.market_data.get_supabase_client"), \
         patch("execution.market_data.get_financial_provider") as mock_factory:
        
        # Config has duplicates
        with patch("core.config.FINANCIAL_PROVIDER", "same"), \
             patch("core.config.FALLBACK_FINANCIAL_PROVIDER", "same"), \
             patch("core.config.SECOND_FALLBACK_FINANCIAL_PROVIDER", "different"):
            
            manager = MarketDataManager()
            
            # Should only call factory twice (for 'same' and 'different')
            assert len(manager.providers) == 2
            assert mock_factory.call_count == 2
