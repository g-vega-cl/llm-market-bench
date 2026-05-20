"""Unit tests for the YFinanceProvider."""

from unittest.mock import MagicMock, patch

import pytest

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
        "exchange": "NMS",
    }

    with patch("yfinance.Ticker", return_value=mock_ticker), patch("core.config.FINANCIAL_API_THROTTLE_SECONDS", 0):
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

    with patch("yfinance.Ticker", return_value=mock_ticker), patch("core.config.FINANCIAL_API_THROTTLE_SECONDS", 0):
        data = await provider.get_ticker_data("INVALID")
        assert data is None


@pytest.mark.asyncio
async def test_yfinance_provider_get_ticker_data_error(caplog):
    """Test error handling in yfinance provider (and that it hardens traceback)."""
    import logging

    caplog.set_level(logging.ERROR)
    provider = YFinanceProvider()

    with (
        patch("yfinance.Ticker", side_effect=Exception("API Error")),
        patch("core.config.FINANCIAL_API_THROTTLE_SECONDS", 0),
    ):
        data = await provider.get_ticker_data("AAPL")
        assert data is None

    # Verify that exception traceback was hardened/logged with engine.execution.providers.yfinance logger
    records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(records) > 0
    assert records[0].name == "engine.execution.providers.yfinance"
    assert "Unexpected error fetching data from yfinance for AAPL" in records[0].message
    assert records[0].exc_info is not None  # traceback captured


@pytest.mark.asyncio
async def test_yfinance_provider_logger_name(caplog):
    """Verify that yfinance provider uses the standardized module-level logger."""
    import logging

    caplog.set_level(logging.WARNING)
    provider = YFinanceProvider()

    mock_ticker = MagicMock()
    mock_ticker.info = {}  # Not found

    with patch("yfinance.Ticker", return_value=mock_ticker), patch("core.config.FINANCIAL_API_THROTTLE_SECONDS", 0):
        await provider.get_ticker_data("INVALID")

    records = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(records) > 0
    assert records[0].name == "engine.execution.providers.yfinance"


@pytest.mark.asyncio
async def test_yfinance_provider_price_fallback_logging(caplog):
    """Verify that price fallbacks are thoroughly logged."""
    import logging

    caplog.set_level(logging.WARNING)
    provider = YFinanceProvider()

    mock_ticker = MagicMock()
    # Missing 'currentPrice', falling back to 'regularMarketPrice'
    mock_ticker.info = {
        "symbol": "AAPL",
        "regularMarketPrice": 145.0,
        "marketCap": 2_500_000_000_000,
        "currency": "USD",
        "exchange": "NMS",
    }

    with patch("yfinance.Ticker", return_value=mock_ticker), patch("core.config.FINANCIAL_API_THROTTLE_SECONDS", 0):
        data = await provider.get_ticker_data("AAPL")
        assert data is not None
        assert data.price == 145.0

    warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert any("currentPrice" in w and "regularMarketPrice" in w for w in warnings)


@pytest.mark.asyncio
async def test_yfinance_provider_market_cap_fallback_logging(caplog):
    """Verify that market cap fallbacks are thoroughly logged."""
    import logging

    caplog.set_level(logging.WARNING)
    provider = YFinanceProvider()

    mock_ticker = MagicMock()
    # Missing 'marketCap', falling back to 'totalAssets'
    mock_ticker.info = {
        "symbol": "AAPL",
        "currentPrice": 150.0,
        "totalAssets": 1_200_000_000,
        "currency": "USD",
        "exchange": "NMS",
    }

    with patch("yfinance.Ticker", return_value=mock_ticker), patch("core.config.FINANCIAL_API_THROTTLE_SECONDS", 0):
        data = await provider.get_ticker_data("AAPL")
        assert data is not None
        assert data.market_cap == 1_200_000_000

    warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert any("marketCap" in w and "totalAssets" in w for w in warnings)
