"""Unit tests for the YFinanceProvider."""

import pytest
from unittest.mock import MagicMock, patch
from execution.providers.yfinance import YFinanceProvider

@pytest.mark.asyncio
async def test_yfinance_provider_get_ticker_data_success():
    """Test successful data retrieval from yfinance."""
    provider = YFinanceProvider()
    
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "symbol": "AAPL",
        "currentPrice": 150.0,
        "marketCap": 2_500_000_000_000,
        "currency": "USD",
        "exchange": "NMS"
    }
    
    with patch("yfinance.Ticker", return_value=mock_ticker):
        data = await provider.get_ticker_data("AAPL")
        
        assert data is not None
        assert data.ticker == "AAPL"
        assert data.price == 150.0
        assert data.market_cap == 2_500_000_000_000
        assert data.currency == "USD"
        assert data.exchange == "NMS"

@pytest.mark.asyncio
async def test_yfinance_provider_get_ticker_data_not_found():
    """Test when a ticker is not found on yfinance."""
    provider = YFinanceProvider()
    
    # yfinance often returns an info dict without the essential keys if not found
    mock_ticker = MagicMock()
    mock_ticker.info = {}
    
    with patch("yfinance.Ticker", return_value=mock_ticker):
        data = await provider.get_ticker_data("INVALID")
        assert data is None

@pytest.mark.asyncio
async def test_yfinance_provider_get_ticker_data_error():
    """Test error handling in yfinance provider."""
    provider = YFinanceProvider()
    
    with patch("yfinance.Ticker", side_effect=Exception("API Error")):
        data = await provider.get_ticker_data("AAPL")
        assert data is None
