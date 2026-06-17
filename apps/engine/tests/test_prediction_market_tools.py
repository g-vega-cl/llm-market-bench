"""Unit tests for prediction market search and odds tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.handlers.base import execute_tool
from core.llm.tools import (
    execute_get_prediction_market_odds_tool,
    execute_search_prediction_markets_tool,
)


@pytest.mark.asyncio
async def test_search_prediction_markets_tool_success():
    """Verify that search_prediction_markets executes the correct DB query and formats the result."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_res = MagicMock()

    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_select
    mock_select.ilike.return_value = mock_select

    mock_res.data = [
        {
            "market_id": "FCUTJUN26",
            "platform": "kalshi",
            "question": "Will the Fed cut interest rates in June?",
            "category": "economics",
            "yes_odds": 0.68,
            "no_odds": 0.32,
            "volume_usd": 140500.0,
            "ends_at": "2026-06-30T23:59:59Z",
        }
    ]
    mock_select.execute.return_value = mock_res

    with patch("core.llm.tools.get_supabase_client", return_value=mock_client):
        result = await execute_search_prediction_markets_tool(query="Fed cut", platform="kalshi")

        # Verify query flow
        mock_client.table.assert_called_once_with("prediction_market_snapshots")
        mock_select.eq.assert_any_call("is_active", True)
        mock_select.eq.assert_any_call("platform", "kalshi")
        mock_select.ilike.assert_called_once_with("question", "%Fed cut%")

        # Verify formatting
        assert "Will the Fed cut interest rates in June?" in result
        assert "KALSHI ID: FCUTJUN26" in result
        assert "YES 68.0%" in result
        assert "NO 32.0%" in result
        assert "Volume: $140,500.00" in result
        assert "Ends At: 2026-06-30T23:59:59Z" in result


@pytest.mark.asyncio
async def test_search_prediction_markets_tool_no_results():
    """Verify response when search has no matches."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_res = MagicMock()

    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_select
    mock_select.ilike.return_value = mock_select

    mock_res.data = []
    mock_select.execute.return_value = mock_res

    with patch("core.llm.tools.get_supabase_client", return_value=mock_client):
        result = await execute_search_prediction_markets_tool(query="nonexistent")
        assert "No active prediction markets found matching 'nonexistent'." in result


@pytest.mark.asyncio
async def test_get_prediction_market_odds_polymarket_success():
    """Verify live Polymarket API odds fetching and parsing."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "question": "Will crypto regulation pass?",
        "volume": 2400000.0,
        "category": "Crypto",
        "outcomePrices": ["0.72", "0.28"],
        "end_date_iso": "2026-08-31T00:00:00Z",
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        result = await execute_get_prediction_market_odds_tool(market_id="12345", platform="polymarket")

        mock_get.assert_called_once_with("https://gamma-api.polymarket.com/markets/12345")
        assert "Polymarket Live Data" in result
        assert "Question: Will crypto regulation pass?" in result
        assert "YES 72.0%" in result
        assert "NO 28.0%" in result
        assert "Total Volume: $2,400,000.00" in result


@pytest.mark.asyncio
async def test_get_prediction_market_odds_kalshi_success():
    """Verify live Kalshi API odds fetching and parsing."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "market": {
            "title": "Will inflation exceed 3%?",
            "volume": 85000,
            "status": "active",
            "yes_bid": 65,
            "no_bid": 35,
            "expiration_time": "2026-10-31T23:59:59Z",
        }
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        result = await execute_get_prediction_market_odds_tool(market_id="INFL3", platform="kalshi")

        mock_get.assert_called_once_with("https://external-api.kalshi.com/trade-api/v2/markets/INFL3")
        assert "Kalshi Live Data" in result
        assert "Question: Will inflation exceed 3%?" in result
        assert "YES 65.0%" in result
        assert "NO 35.0%" in result
        assert "Volume: 85,000 contracts" in result


@pytest.mark.asyncio
async def test_base_handler_executes_tools():
    """Verify dispatcher routing for the two new tools in execute_tool."""
    with (
        patch("core.llm.tools.execute_search_prediction_markets_tool", new_callable=AsyncMock) as mock_search,
        patch("core.llm.tools.execute_get_prediction_market_odds_tool", new_callable=AsyncMock) as mock_odds,
    ):
        mock_search.return_value = "search_result"
        mock_odds.return_value = "odds_result"

        res1 = await execute_tool("search_prediction_markets", {"query": "test_query", "platform": "kalshi"}, "model_1")
        mock_search.assert_called_once_with("test_query", platform="kalshi")
        assert res1 == "search_result"

        res2 = await execute_tool(
            "get_prediction_market_odds", {"market_id": "m1", "platform": "polymarket"}, "model_1"
        )
        mock_odds.assert_called_once_with("m1", platform="polymarket")
        assert res2 == "odds_result"
