"""TDD Tests for get_treasury_yield_curve tool."""

from unittest.mock import AsyncMock, patch

import pytest

from core.llm.handlers.base import execute_tool
from core.llm.tools import (
    CANONICAL_TOOLS_REGISTRY,
    execute_get_treasury_yield_curve_tool,
)


@pytest.mark.asyncio
async def test_treasury_yield_curve_tool_registered():
    """Verify get_treasury_yield_curve is in CANONICAL_TOOLS_REGISTRY."""
    assert "get_treasury_yield_curve" in CANONICAL_TOOLS_REGISTRY
    tool_def = CANONICAL_TOOLS_REGISTRY["get_treasury_yield_curve"]
    assert tool_def["function"]["name"] == "get_treasury_yield_curve"
    assert "description" in tool_def["function"]


@pytest.mark.asyncio
async def test_treasury_yield_curve_tool_execution():
    """Verify tool executes and outputs clean markdown with tenors and spreads."""

    async def mock_fetch_fred(series_id_or_alias, lookback_periods=2, **kwargs):
        series_map = {
            "treasury_3m": (4.85, 4.80),
            "DGS3MO": (4.85, 4.80),
            "treasury_2y": (3.92, 3.95),
            "DGS2": (3.92, 3.95),
            "treasury_5y": (3.85, 3.88),
            "DGS5": (3.85, 3.88),
            "treasury_10y": (4.15, 4.10),
            "DGS10": (4.15, 4.10),
            "treasury_30y": (4.45, 4.40),
            "DGS30": (4.45, 4.40),
            "yield_curve_10y2y": (0.23, 0.15),
            "T10Y2Y": (0.23, 0.15),
        }
        prev_val, curr_val = series_map.get(series_id_or_alias, (4.0, 4.0))
        return {
            "series_id": series_id_or_alias,
            "title": f"Treasury {series_id_or_alias}",
            "units": "Percent",
            "frequency": "Daily",
            "latest_date": "2026-10-06",
            "latest_value": curr_val,
            "observations": [
                {"date": "2026-10-05", "value": prev_val},
                {"date": "2026-10-06", "value": curr_val},
            ],
        }

    with patch("core.fred.fetch_fred_series_observations", side_effect=mock_fetch_fred):
        result = await execute_get_treasury_yield_curve_tool()
        assert "US Treasury Yield Curve" in result
        assert "2-Year" in result or "DGS2" in result
        assert "10-Year" in result or "DGS10" in result
        assert "30-Year" in result or "DGS30" in result
        assert "10Y - 2Y" in result or "T10Y2Y" in result
        # Check calculation of 1d bps change (4.10 - 4.15 = -0.05% = -5.0 bps)
        assert "4.10%" in result
        assert "-5.0 bps" in result or "-0.05" in result


@pytest.mark.asyncio
async def test_treasury_yield_curve_dispatch():
    """Verify base execute_tool dispatches to get_treasury_yield_curve."""
    with patch(
        "core.llm.tools.execute_get_treasury_yield_curve_tool",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_exec.return_value = "### Mock Yield Curve"
        res = await execute_tool("get_treasury_yield_curve", {}, "test_model")
        assert res == "### Mock Yield Curve"
        mock_exec.assert_called_once()
