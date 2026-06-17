"""Unit tests for individual company earnings tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm import tools
from core.llm.handlers.base import execute_tool
from execution.providers.fmp import FMPProvider


@pytest.mark.asyncio
async def test_fmp_provider_get_earnings_history():
    provider = FMPProvider()
    provider.api_key = "test_api_key"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "symbol": "AAPL",
            "date": "2026-07-30",
            "epsActual": None,
            "epsEstimated": 1.88,
            "revenueActual": None,
            "revenueEstimated": 108400600000.0,
            "lastUpdated": "2026-06-17",
        },
        {
            "symbol": "AAPL",
            "date": "2026-04-30",
            "epsActual": 2.01,
            "epsEstimated": 1.95,
            "revenueActual": 111184000000.0,
            "revenueEstimated": 109457600000.0,
            "lastUpdated": "2026-06-17",
        },
    ]
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        history = await provider.get_earnings_history("AAPL", limit=2)

        assert len(history) == 2

        # Check upcoming
        h0 = history[0]
        assert h0["symbol"] == "AAPL"
        assert h0["date"] == "2026-07-30"
        assert h0["epsActual"] is None
        assert h0["epsEstimated"] == 1.88
        assert h0["isUpcoming"] is True

        # Check past/surprise
        h1 = history[1]
        assert h1["symbol"] == "AAPL"
        assert h1["date"] == "2026-04-30"
        assert h1["epsActual"] == 2.01
        assert h1["epsEstimated"] == 1.95
        assert pytest.approx(h1["surprisePct"], 0.01) == ((2.01 - 1.95) / 1.95) * 100
        assert h1["isUpcoming"] is False


@pytest.mark.asyncio
async def test_execute_earnings_history_tool():
    mock_history = [
        {
            "symbol": "AAPL",
            "date": "2026-07-30",
            "epsActual": None,
            "epsEstimated": 1.88,
            "revenueActual": None,
            "revenueEstimated": 108400600000.0,
            "surprisePct": None,
            "isUpcoming": True,
        },
        {
            "symbol": "AAPL",
            "date": "2026-04-30",
            "epsActual": 2.01,
            "epsEstimated": 1.95,
            "revenueActual": 111184000000.0,
            "revenueEstimated": 109457600000.0,
            "surprisePct": 3.07,
            "isUpcoming": False,
        },
    ]

    with patch("execution.market_data.MarketDataManager.get_earnings_history", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_history
        result = await tools.execute_earnings_history_tool("AAPL", limit=2)

        assert "AAPL" in result
        assert "Upcoming Earnings Announcement" in result
        assert "Historical Earnings Reports" in result
        assert "2.01" in result
        assert "3.07%" in result
        assert "108.40B" in result


@pytest.mark.asyncio
async def test_execute_tool_dispatches_get_earnings_history():
    with patch("core.llm.tools.execute_earnings_history_tool", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = "Mocked earnings response"

        res = await execute_tool("get_earnings_history", {"ticker": "AAPL", "limit": 4}, "model-xyz")

        assert res == "Mocked earnings response"
        mock_execute.assert_called_once_with("AAPL", limit=4)
