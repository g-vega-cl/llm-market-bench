"""Unit tests for execute_stock_tool during pre-market and regular hours."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.tools import execute_stock_tool
from execution.providers.base import TickerData


@pytest.mark.asyncio
async def test_execute_stock_tool_regular_hours():
    """Test execute_stock_tool returns standard quote during regular hours."""
    mock_mdm = MagicMock()
    mock_mdm.get_quote = AsyncMock(return_value=TickerData(ticker="NVDA", price=125.50, market_cap=3e12, exists=True))
    mock_mdm.is_premarket = AsyncMock(return_value=False)

    with patch("core.llm.tools.MarketDataManager", return_value=mock_mdm):
        res = await execute_stock_tool("NVDA")
        assert "Ticker: NVDA" in res
        assert "Current Price: $125.50" in res
        assert "Market Cap: $3000.00B" in res
        assert "Session: PRE-MARKET" not in res


@pytest.mark.asyncio
async def test_execute_stock_tool_premarket_hours():
    """Test execute_stock_tool includes pre-market price, previous close and gap during pre-market."""
    mock_mdm = MagicMock()
    mock_mdm.get_quote = AsyncMock(return_value=TickerData(ticker="NVDA", price=125.50, market_cap=3e12, exists=True))
    mock_mdm.is_premarket = AsyncMock(return_value=True)
    mock_mdm.get_premarket_quote = AsyncMock(
        return_value={
            "price": 128.00,
            "previous_close": 125.00,
            "change": 3.00,
            "change_pct": 2.40,
        }
    )

    with patch("core.llm.tools.MarketDataManager", return_value=mock_mdm):
        res = await execute_stock_tool("NVDA")
        assert "Ticker: NVDA" in res
        assert "Session: PRE-MARKET" in res
        assert "Pre-Market Price: $128.00" in res
        assert "Previous Close: $125.00" in res
        assert "Overnight Gap: +3.00 (+2.40%)" in res
        assert "Market Cap: $3000.00B" in res
