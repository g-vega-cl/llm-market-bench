from unittest.mock import AsyncMock, patch

import pytest

from core.llm.handlers.base import execute_tool
from core.llm.tools import CANONICAL_TOOLS_REGISTRY


@pytest.mark.asyncio
async def test_tools_registered():
    """Verify the new tools are registered in the registry."""
    assert "get_global_macro_context" in CANONICAL_TOOLS_REGISTRY
    assert "get_volatility_index_details" in CANONICAL_TOOLS_REGISTRY


@pytest.mark.asyncio
async def test_get_global_macro_context_routing():
    """Verify routing and execution of get_global_macro_context tool."""
    with patch("core.llm.tools.execute_get_global_macro_context_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = "Mock Macro Context"
        res = await execute_tool("get_global_macro_context", {}, "test_model")
        assert res == "Mock Macro Context"
        mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_get_volatility_index_details_routing():
    """Verify routing and execution of get_volatility_index_details tool."""
    with patch("core.llm.tools.execute_get_volatility_index_details_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = "Mock Volatility Details"
        res = await execute_tool("get_volatility_index_details", {"lookback_days": 30}, "test_model")
        assert res == "Mock Volatility Details"
        mock_exec.assert_called_once_with(30)


@pytest.mark.asyncio
async def test_execute_get_volatility_index_details_calculation():
    """Verify the calculations inside execute_get_volatility_index_details_tool."""
    from core.llm.tools import execute_get_volatility_index_details_tool

    # Mock historical price data for VIXY, VIXM, and SPY
    # Descending order (newest first)
    mock_vixy_history = [
        {"price": 15.0, "fetched_at": "2026-07-22 00:00"},
        {"price": 14.8, "fetched_at": "2026-07-21 00:00"},
        {"price": 14.5, "fetched_at": "2026-07-20 00:00"},
        {"price": 14.0, "fetched_at": "2026-07-19 00:00"},
        {"price": 13.5, "fetched_at": "2026-07-18 00:00"},
    ]
    mock_vixm_history = [
        {"price": 20.0, "fetched_at": "2026-07-22 00:00"},
        {"price": 19.9, "fetched_at": "2026-07-21 00:00"},
        {"price": 19.8, "fetched_at": "2026-07-20 00:00"},
        {"price": 19.7, "fetched_at": "2026-07-19 00:00"},
        {"price": 19.5, "fetched_at": "2026-07-18 00:00"},
    ]
    # SPY should be inversely correlated to VIXY
    mock_spy_history = [
        {"price": 500.0, "fetched_at": "2026-07-22 00:00"},
        {"price": 502.0, "fetched_at": "2026-07-21 00:00"},
        {"price": 505.0, "fetched_at": "2026-07-20 00:00"},
        {"price": 510.0, "fetched_at": "2026-07-19 00:00"},
        {"price": 515.0, "fetched_at": "2026-07-18 00:00"},
    ]

    async def mock_get_history(ticker, days, **kwargs):
        if ticker == "VIXY":
            return mock_vixy_history[:days]
        elif ticker == "VIXM":
            return mock_vixm_history[:days]
        elif ticker == "SPY":
            return mock_spy_history[:days]
        return []

    with patch("execution.market_data.MarketDataManager.get_history", side_effect=mock_get_history):
        res = await execute_get_volatility_index_details_tool(lookback_days=5)

        assert "Volatility Index" in res
        assert "VIXY" in res
        assert "VIXM" in res


@pytest.mark.asyncio
async def test_execute_get_volatility_index_details_spot_vix_vs_vixy_separation():
    """Verify spot Cboe VIX (^VIX) determines the true volatility regime while VIXY/VIXM measure term structure."""
    from core.llm.tools import execute_get_volatility_index_details_tool

    # ^VIX: Spot index is elevated at 24.50 (high percentile)
    mock_vix_history = [
        {"price": 24.5, "fetched_at": "2026-07-22 00:00"},
        {"price": 23.0, "fetched_at": "2026-07-21 00:00"},
        {"price": 21.0, "fetched_at": "2026-07-20 00:00"},
        {"price": 18.0, "fetched_at": "2026-07-19 00:00"},
        {"price": 16.0, "fetched_at": "2026-07-18 00:00"},
    ]
    # VIXY: Futures ETF has decayed to a low price of $11.50 (lowest in range due to contango)
    mock_vixy_history = [
        {"price": 11.5, "fetched_at": "2026-07-22 00:00"},
        {"price": 12.0, "fetched_at": "2026-07-21 00:00"},
        {"price": 13.0, "fetched_at": "2026-07-20 00:00"},
        {"price": 14.0, "fetched_at": "2026-07-19 00:00"},
        {"price": 15.0, "fetched_at": "2026-07-18 00:00"},
    ]
    mock_vixm_history = [
        {"price": 20.0, "fetched_at": "2026-07-22 00:00"},
        {"price": 20.5, "fetched_at": "2026-07-21 00:00"},
        {"price": 21.0, "fetched_at": "2026-07-20 00:00"},
        {"price": 21.5, "fetched_at": "2026-07-19 00:00"},
        {"price": 22.0, "fetched_at": "2026-07-18 00:00"},
    ]
    mock_spy_history = [
        {"price": 500.0, "fetched_at": "2026-07-22 00:00"},
        {"price": 505.0, "fetched_at": "2026-07-21 00:00"},
        {"price": 510.0, "fetched_at": "2026-07-20 00:00"},
        {"price": 515.0, "fetched_at": "2026-07-19 00:00"},
        {"price": 520.0, "fetched_at": "2026-07-18 00:00"},
    ]

    async def mock_get_history(ticker, days, **kwargs):
        if ticker == "^VIX":
            return mock_vix_history[:days]
        elif ticker == "VIXY":
            return mock_vixy_history[:days]
        elif ticker == "VIXM":
            return mock_vixm_history[:days]
        elif ticker == "SPY":
            return mock_spy_history[:days]
        return []

    with patch("execution.market_data.MarketDataManager.get_history", side_effect=mock_get_history):
        res = await execute_get_volatility_index_details_tool(lookback_days=5)

        # 1. Output must distinguish Spot VIX from Futures ETFs
        assert "Cboe Volatility Index (Spot VIX: ^VIX)" in res
        assert "Spot VIX Level:" in res and "24.50" in res

        # 2. Volatility regime must reflect elevated spot VIX (24.50), NOT VIXY's decaying price
        assert "ELEVATED VOLATILITY" in res
        assert "COMPLACENCY ZONE" not in res

        # 3. Term structure section must cover VIXY/VIXM
        assert "VIX Futures Term Structure & Roll Dynamics" in res
        assert "VIXY (Short-Term Futures ETF)" in res

        # 4. Must include explicit roll decay warning
        assert "contango roll decay" in res.lower()
