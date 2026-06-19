"""Unit tests for get_key_metrics fundamental analysis tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm import tools
from core.llm.handlers.base import execute_tool
from execution.market_data import MarketDataManager
from execution.providers.fmp import FMPProvider


@pytest.mark.asyncio
async def test_fmp_provider_get_key_metrics():
    """Test FMPProvider.get_key_metrics returns standardized key metrics."""
    provider = FMPProvider()
    provider.api_key = "test_api_key"

    def mock_get_impl(url, params=None):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        if "key-metrics" in url:
            mock_resp.json.return_value = [
                {
                    "symbol": "AAPL",
                    "date": "2024-09-28",
                    "fiscalYear": "2024",
                    "period": "FY",
                    "evToEBITDA": 24.3,
                    "freeCashFlowYield": 0.035,
                    "ignoredField": "should_not_be_present",
                }
            ]
        elif "ratios" in url:
            mock_resp.json.return_value = [
                {
                    "symbol": "AAPL",
                    "date": "2024-09-28",
                    "fiscalYear": "2024",
                    "period": "FY",
                    "priceToEarningsRatio": 30.5,
                    "priceToSalesRatio": 8.2,
                    "priceToBookRatio": 45.1,
                    "debtToEquityRatio": 2.1,
                    "currentRatio": 1.2,
                    "returnOnEquity": 1.75,
                    "dividendYield": 0.005,
                    "bookValuePerShare": 4.5,
                    "revenuePerShare": 24.5,
                    "netIncomePerShare": 6.1,
                    "freeCashFlowPerShare": 7.2,
                }
            ]
        return mock_resp

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=mock_get_impl) as mock_get:
        metrics = await provider.get_key_metrics("AAPL", period="annual", limit=1)

        assert len(metrics) == 1
        m = metrics[0]
        assert m["symbol"] == "AAPL"
        assert m["date"] == "2024-09-28"
        assert m["peRatio"] == 30.5
        assert m["pbRatio"] == 45.1
        assert m["enterpriseValueOverEBITDA"] == 24.3
        assert m["freeCashFlowYield"] == 0.035
        assert m["priceToFreeCashFlowsRatio"] == pytest.approx(1.0 / 0.035)
        assert "ignoredField" not in m

        # Check API parameters
        assert mock_get.call_count == 2
        for call in mock_get.call_args_list:
            args, kwargs = call
            params = kwargs.get("params")
            assert params["apikey"] == "test_api_key"
            assert params["period"] == "annual"
            assert params["limit"] == 1


@pytest.mark.asyncio
async def test_market_data_manager_get_key_metrics():
    """Test MarketDataManager delegates to provider and returns results."""
    # We will mock the provider
    mock_provider = MagicMock()
    mock_provider.get_key_metrics = AsyncMock(return_value=[{"symbol": "AAPL", "peRatio": 30.5}])

    manager = MarketDataManager()
    manager.providers = [mock_provider]

    metrics = await manager.get_key_metrics("AAPL", period="annual", limit=2)
    assert len(metrics) == 1
    assert metrics[0]["peRatio"] == 30.5
    mock_provider.get_key_metrics.assert_called_once_with("AAPL", "annual", 2)


@pytest.mark.asyncio
async def test_execute_key_metrics_tool():
    """Test execute_key_metrics_tool formats and executes correctly."""
    mock_metrics = [
        {
            "symbol": "AAPL",
            "date": "2024-09-28",
            "calendarYear": "2024",
            "period": "FY",
            "peRatio": 30.5,
            "debtToEquity": 2.1,
            "roe": 1.75,
            "priceToFreeCashFlowsRatio": 28.57,
        }
    ]

    with patch.object(MarketDataManager, "get_key_metrics", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_metrics
        result = await tools.execute_key_metrics_tool("AAPL", period="annual", limit=1)

        assert "AAPL" in result
        assert "30.5" in result
        assert "2.1" in result
        assert "ROE: 175.00%" in result
        assert "Price/Free Cash Flow Ratio: 28.57" in result
        mock_get.assert_called_once_with("AAPL", "annual", 1)


@pytest.mark.asyncio
async def test_execute_tool_dispatches_get_key_metrics():
    """Test execute_tool dispatches 'get_key_metrics' correctly."""
    with patch("core.llm.tools.execute_key_metrics_tool", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = "Mocked metrics response"

        res = await execute_tool("get_key_metrics", {"ticker": "AAPL", "period": "quarter", "limit": 2}, "model-xyz")

        assert res == "Mocked metrics response"
        mock_execute.assert_called_once_with("AAPL", period="quarter", limit=2)


@pytest.mark.asyncio
async def test_fmp_provider_get_key_metrics_fallback_to_annual():
    """Test that get_key_metrics falls back to annual if quarterly returns a client error (e.g. 402/403)."""
    provider = FMPProvider()
    provider.api_key = "test_api_key"

    def mock_get_impl(url, params=None):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        if params and params.get("period") == "quarter":
            mock_resp.status_code = 402
            mock_resp.json.return_value = []
        else:
            mock_resp.status_code = 200
            if "key-metrics" in url:
                mock_resp.json.return_value = [
                    {
                        "symbol": "AAPL",
                        "date": "2024-09-28",
                        "fiscalYear": "2024",
                        "period": "FY",
                        "evToEBITDA": 24.3,
                        "freeCashFlowYield": 0.035,
                    }
                ]
            elif "ratios" in url:
                mock_resp.json.return_value = [
                    {
                        "symbol": "AAPL",
                        "date": "2024-09-28",
                        "fiscalYear": "2024",
                        "period": "FY",
                        "priceToEarningsRatio": 30.5,
                    }
                ]
        return mock_resp

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=mock_get_impl) as mock_get:
        metrics = await provider.get_key_metrics("AAPL", period="quarter", limit=1)

        assert len(metrics) == 1
        assert metrics[0]["symbol"] == "AAPL"
        assert metrics[0]["peRatio"] == 30.5
        assert mock_get.call_count == 4
