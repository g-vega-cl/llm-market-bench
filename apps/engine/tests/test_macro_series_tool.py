"""Tests for the get_macro_economic_series tool and autoresearcher integration."""

from unittest.mock import AsyncMock, patch

import pytest

from autoresearch.researcher import PromptResearchResult
from core.llm.handlers.base import execute_tool
from core.llm.tools import CANONICAL_TOOLS_REGISTRY, execute_macro_economic_series_tool


@pytest.mark.asyncio
async def test_macro_series_tool_registered():
    """Verify get_macro_economic_series is registered in CANONICAL_TOOLS_REGISTRY."""
    assert "get_macro_economic_series" in CANONICAL_TOOLS_REGISTRY
    tool_def = CANONICAL_TOOLS_REGISTRY["get_macro_economic_series"]
    assert tool_def["function"]["name"] == "get_macro_economic_series"
    assert "series_id_or_alias" in tool_def["function"]["parameters"]["properties"]


@pytest.mark.asyncio
async def test_macro_series_tool_execution():
    """Verify tool execution formats output as markdown."""
    with patch("core.fred.fetch_fred_series_observations", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {
            "series_id": "T10Y2Y",
            "title": "10-Year Treasury Constant Maturity Minus 2-Year Treasury",
            "units": "Percent",
            "frequency": "Daily",
            "latest_date": "2026-08-18",
            "latest_value": 0.15,
            "observations": [
                {"date": "2026-08-17", "value": 0.12},
                {"date": "2026-08-18", "value": 0.15},
            ],
        }

        res = await execute_macro_economic_series_tool(series_id_or_alias="yield_curve_10y2y", lookback_periods=5)
        assert "FRED Macro Series" in res
        assert "T10Y2Y" in res
        assert "0.15" in res


@pytest.mark.asyncio
async def test_macro_series_tool_handler_routing():
    """Verify execute_tool correctly routes to execute_macro_economic_series_tool."""
    with patch("core.llm.tools.execute_macro_economic_series_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = "Mock Macro Series Result"
        res = await execute_tool(
            "get_macro_economic_series",
            {"series_id_or_alias": "fed_funds", "lookback_periods": 3},
            "test_model",
        )
        assert res == "Mock Macro Series Result"
        mock_exec.assert_called_once_with("fed_funds", lookback_periods=3, units="lin", frequency=None)


def test_autoresearcher_selected_tools_schema():
    """Verify PromptResearchResult accepts get_macro_economic_series."""
    result = PromptResearchResult(
        new_prompt_text="Updated prompt",
        selected_tools=["get_stock_quote", "get_macro_economic_series"],
        selected_prompt_blocks=["let_winners_run"],
        change_description="Added FRED macro tool",
        experiment_type="incremental",
        research_reasoning="Macro trend awareness",
        confidence=85,
    )
    assert "get_macro_economic_series" in result.selected_tools
