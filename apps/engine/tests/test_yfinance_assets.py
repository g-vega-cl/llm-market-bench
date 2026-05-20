from unittest.mock import MagicMock, patch

import pytest

from execution.providers.yfinance import YFinanceProvider


@pytest.mark.asyncio
async def test_yfinance_get_ticker_data_etf_assets():
    """Verify that yfinance provider falls back to totalAssets or netAssets for market_cap."""
    provider = YFinanceProvider()

    # Mock yfinance Ticker and info
    mock_ticker = MagicMock()

    # Case 1: totalAssets fallback
    mock_ticker.info = {"symbol": "BDRY", "regularMarketPrice": 12.5, "totalAssets": 41473776}

    with patch("yfinance.Ticker", return_value=mock_ticker), patch("core.config.FINANCIAL_API_THROTTLE_SECONDS", 0):
        data = await provider.get_ticker_data("BDRY")
        assert data is not None
        assert data.market_cap == 41473776

    # Case 2: netAssets fallback
    mock_ticker.info = {"symbol": "BDRY", "regularMarketPrice": 12.5, "netAssets": 50000000}

    with patch("yfinance.Ticker", return_value=mock_ticker), patch("core.config.FINANCIAL_API_THROTTLE_SECONDS", 0):
        data = await provider.get_ticker_data("BDRY")
        assert data is not None
        assert data.market_cap == 50000000

    # Case 3: marketCap priority
    mock_ticker.info = {
        "symbol": "XLE",
        "regularMarketPrice": 100.0,
        "marketCap": 1000000000,
        "totalAssets": 5000000000,
    }

    with patch("yfinance.Ticker", return_value=mock_ticker), patch("core.config.FINANCIAL_API_THROTTLE_SECONDS", 0):
        data = await provider.get_ticker_data("XLE")
        assert data is not None
        assert data.market_cap == 1000000000
