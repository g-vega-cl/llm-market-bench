from unittest.mock import AsyncMock, patch

import pytest

from core.llm.tools import execute_price_history_tool


@pytest.mark.asyncio
async def test_execute_price_history_tool_includes_volume():
    mock_history = [
        {"fetched_at": "2026-06-14", "price": 150.0, "volume": 1000000},
        {"fetched_at": "2026-06-13", "price": 145.0, "volume": 1200000},
        {"fetched_at": "2026-06-12", "price": 140.0, "volume": 800000},
        {"fetched_at": "2026-06-11", "price": 135.0, "volume": 900000},
        {"fetched_at": "2026-06-10", "price": 130.0, "volume": 1100000},
    ]
    
    with patch("core.llm.tools.MarketDataManager") as mock_mgr_class:
        mock_mgr_instance = mock_mgr_class.return_value
        mock_mgr_instance.get_history = AsyncMock(return_value=mock_history)
        
        result = await execute_price_history_tool("AAPL", days=5)
        
        # Test that daily volume is included
        assert "Volume:" in result, "Daily volume is not included in the output"
        assert "1000000" in result, "Volume value is missing"
        
        # Test that ADV/RVOL volume context is appended
        assert "Volume Context:" in result, "Volume context (ADV/RVOL) is not appended"
