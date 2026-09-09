"""Tests for Catalyst Radar LLM tool calling, schema, and agent integration."""

from unittest.mock import patch

import pytest

from analysis.catalyst_radar import CatalystRadarItem


@pytest.mark.asyncio
async def test_execute_get_catalyst_radar_tool():
    """Verify tool handler formats radar items into markdown table."""
    from core.llm.tools import execute_get_catalyst_radar_tool

    sample_items = [
        CatalystRadarItem(
            concept_id="c1",
            concept_name="Semiconductor Export Controls",
            velocity_score=3.2,
            catalyst_id="m1",
            catalyst_title="TSMC Monthly Revenue Report",
            target_date="2026-09-16",
            days_to_event=7,
            stage="upcoming",
            date_offset_label="1 week from now",
            impact="BULLISH",
            similarity=0.88,
            memory_content="Detailed note on foundry capex",
            related_tickers=["TSM"],
        ),
        CatalystRadarItem(
            concept_id="c2",
            concept_name="Antitrust Remedies",
            velocity_score=2.1,
            catalyst_id="m2",
            catalyst_title="DOJ Google Remedies Hearing",
            target_date="2026-09-08",
            days_to_event=-1,
            stage="digesting",
            date_offset_label="digesting, 1 day ago",
            impact="BEARISH",
            similarity=0.79,
            memory_content="DOJ filings detail break-up provisions",
            related_tickers=["GOOGL"],
        ),
    ]

    with patch("analysis.catalyst_radar.fetch_catalyst_radar", return_value=sample_items):
        res = await execute_get_catalyst_radar_tool(days_ahead=7, include_digesting=True, detail=False)

    assert "Catalyst Radar (Keep an Eye)" in res
    assert "Semiconductor Export Controls" in res
    assert "1 week from now" in res
    assert "digesting, 1 day ago" in res
    assert "| Upcoming |" in res or "upcoming" in res.lower()
    assert "| Digesting |" in res or "digesting" in res.lower()


def test_catalyst_radar_tool_in_canonical_registry():
    """Verify get_catalyst_radar is registered in CANONICAL_TOOLS_REGISTRY with valid schema."""
    from core.llm.tools import CANONICAL_TOOLS_REGISTRY

    assert "get_catalyst_radar" in CANONICAL_TOOLS_REGISTRY
    tool_def = CANONICAL_TOOLS_REGISTRY["get_catalyst_radar"]

    assert tool_def["type"] == "function"
    assert tool_def["function"]["name"] == "get_catalyst_radar"
    params = tool_def["function"]["parameters"]["properties"]
    assert "days_ahead" in params
    assert "include_digesting" in params
    assert "min_velocity" in params
    assert "detail" in params
