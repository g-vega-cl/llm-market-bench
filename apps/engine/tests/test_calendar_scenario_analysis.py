"""Tests for forward calendar, scenario analysis, and date/time anchoring."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from analysis.calendar_scenarios import (
    calculate_target_window,
    execute_get_calendar_scenario_analysis_tool,
)
from core.llm.handlers.base import execute_tool
from core.llm.tools import (
    CANONICAL_TOOLS_REGISTRY,
    to_anthropic,
    to_gemini,
)
from core.time_utils import get_current_day_info

# ---------------------------------------------------------------------------
# 1. Date, Exact Time & Session Phase Anchoring Tests
# ---------------------------------------------------------------------------


def test_get_current_day_info_premarket():
    """Verify exact time, timezone, and Pre-Market session phase formatting."""
    fixed_time = datetime(2026, 9, 10, 8, 30, 0, tzinfo=ZoneInfo("America/New_York"))
    info = get_current_day_info(now=fixed_time)

    assert "Thursday, September 10, 2026" in info
    assert "08:30:00 AM EDT" in info
    assert "12:30:00 UTC" in info
    assert "Market Session: Pre-Market (04:00 - 09:30 EDT)" in info
    assert "Tomorrow: Friday, September 11, 2026" in info
    assert "Next Week: Monday, September 14, 2026 to Friday, September 18, 2026" in info


def test_get_current_day_info_regular_hours():
    """Verify Regular Trading Hours formatting during active market."""
    fixed_time = datetime(2026, 9, 10, 14, 15, 30, tzinfo=ZoneInfo("America/New_York"))
    info = get_current_day_info(now=fixed_time)

    assert "02:15:30 PM EDT" in info
    assert "Market Session: Regular Trading Hours (09:30 - 16:00 EDT)" in info


def test_get_current_day_info_postmarket():
    """Verify Post-Market / After-Hours formatting."""
    fixed_time = datetime(2026, 9, 10, 17, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    info = get_current_day_info(now=fixed_time)

    assert "05:00:00 PM EDT" in info
    assert "Market Session: Post-Market / After-Hours (16:00 - 20:00 EDT)" in info


def test_get_current_day_info_weekend_closed():
    """Verify weekend closed state formatting."""
    fixed_time = datetime(2026, 9, 12, 11, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    info = get_current_day_info(now=fixed_time)

    assert "Saturday, September 12, 2026" in info
    assert "Market Session: Closed (Weekend)" in info


# ---------------------------------------------------------------------------
# 2. Canonical Tool Schema & Registry Contracts
# ---------------------------------------------------------------------------


def test_tool_registered_in_canonical_registry():
    """Verify get_calendar_scenario_analysis is in CANONICAL_TOOLS_REGISTRY."""
    assert "get_calendar_scenario_analysis" in CANONICAL_TOOLS_REGISTRY
    tool_def = CANONICAL_TOOLS_REGISTRY["get_calendar_scenario_analysis"]
    fn = tool_def["function"]

    assert fn["name"] == "get_calendar_scenario_analysis"
    assert "timeframe" in fn["parameters"]["properties"]
    assert "ticker" in fn["parameters"]["properties"]
    assert "include_historical_memories" in fn["parameters"]["properties"]


def test_tool_adapter_translations():
    """Verify tool translates cleanly to Anthropic and Gemini schemas."""
    canonical = CANONICAL_TOOLS_REGISTRY["get_calendar_scenario_analysis"]

    anthropic_tool = to_anthropic(canonical)
    assert anthropic_tool["name"] == "get_calendar_scenario_analysis"
    assert "input_schema" in anthropic_tool

    gemini_tool = to_gemini(canonical)
    assert gemini_tool["name"] == "get_calendar_scenario_analysis"
    assert "parameters" in gemini_tool


# ---------------------------------------------------------------------------
# 3. Window Calculation Tests
# ---------------------------------------------------------------------------


def test_calculate_target_window_tomorrow():
    ref = datetime(2026, 9, 10, tzinfo=UTC).date()
    start, end, label = calculate_target_window("tomorrow", ref_date=ref)
    assert str(start) == "2026-09-11"
    assert str(end) == "2026-09-11"
    assert "Tomorrow" in label


def test_calculate_target_window_next_week():
    ref = datetime(2026, 9, 10, tzinfo=UTC).date()
    start, end, label = calculate_target_window("next_week", ref_date=ref)
    assert str(start) == "2026-09-11"
    assert str(end) == "2026-09-18"


# ---------------------------------------------------------------------------
# 4. End-to-End Tool Execution with Mocked Supabase (Calendar + Scenarios + Memories)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_get_calendar_scenario_analysis_flow():
    """Test full retrieval flow: calendar triggers, scenarios, trading plans, and past memories."""
    mock_memories = [
        # Scheduled Calendar Event for Tomorrow
        {
            "id": "cal-001",
            "content": "[CALENDAR EVENT] (08:30 AM) 2026-09-11: US Core CPI YoY: Headline inflation print | Impact: HIGH | Date: 2026-09-11",
            "memory_type": "CALENDAR_EVENT",
            "target_date": "2026-09-11",
            "importance_score": 9,
            "metadata": {
                "is_calendar_event": True,
                "event_time": "08:30 AM",
                "impact": "HIGH",
            },
        },
        # Macro Consensus Event with Scenarios for Next Week
        {
            "id": "cons-001",
            "content": "FOMC Interest Rate Decision and economic projections",
            "memory_type": "consensus_event",
            "target_date": "2026-09-16",
            "importance_score": 10,
            "metadata": {
                "type": "consensus_event",
                "event_name": "September FOMC Rate Decision",
                "impact": "HIGH",
                "scenario_analysis": "Bull: Rate cut 25bps (Plan: Buy QQQ). Bear: Hold hawkish (Plan: Buy XLE/TLT put).",
                "scenarios": [
                    {
                        "header": "25bps Rate Cut (Bull Case)",
                        "probability": 65,
                        "description": "Fed begins easing cycle amid cooling labor demand.",
                        "trading_plan": "Long tech and interest-rate sensitives (QQQ, IWM).",
                        "assets": [{"ticker": "QQQ", "reason": "Multiple expansion on tech."}],
                    },
                    {
                        "header": "Hawkish Pause (Bear Case)",
                        "probability": 35,
                        "description": "Inflation sticky, rates held higher for longer.",
                        "trading_plan": "Short duration, buy defensive energy/cash.",
                        "assets": [{"ticker": "TLT", "reason": "Yield surge causes bond selloff."}],
                    },
                ],
                "discovered_assets": ["QQQ", "IWM", "TLT"],
            },
        },
        # Historical Precedent Memory (Lessons Learned from Past Event)
        {
            "id": "mem-hist-001",
            "content": "Lesson from July 2026 CPI: When core print matched consensus but shelter stayed hot, tech sold off for the first 90 mins then rebounded aggressively.",
            "memory_type": "LESSON",
            "target_date": None,
            "importance_score": 8,
            "metadata": {"tags": ["CPI", "macro", "lesson"], "historical_parallel": "July 2026 CPI Reversal"},
        },
    ]

    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=mock_memories)
    mock_client.table.return_value = mock_query

    with (
        patch("analysis.calendar_scenarios.get_supabase_client", return_value=mock_client),
        patch("core.time_utils.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = datetime(2026, 9, 10, 9, 30, 0, tzinfo=ZoneInfo("America/New_York"))

        result = await execute_get_calendar_scenario_analysis_tool(
            timeframe="next_week",
            include_historical_memories=True,
            detail=True,
            ref_date=datetime(2026, 9, 10, tzinfo=UTC).date(),
        )

        # Assertions on formatted markdown context
        assert "US Core CPI YoY" in result
        assert "September FOMC Rate Decision" in result
        assert "25bps Rate Cut (Bull Case)" in result
        assert "Long tech and interest-rate sensitives (QQQ, IWM)" in result
        assert "QQQ" in result
        assert "July 2026 CPI Reversal" in result or "Lesson from July 2026 CPI" in result


# ---------------------------------------------------------------------------
# 5. Handler Dispatch Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handler_dispatch_get_calendar_scenario_analysis():
    """Verify tool dispatches via core.llm.handlers.base.execute_tool."""
    with patch(
        "core.llm.tools.execute_get_calendar_scenario_analysis_tool",
        new_callable=AsyncMock,
        return_value="MOCK_SCENARIO_RESULT",
    ):
        res = await execute_tool("get_calendar_scenario_analysis", {"timeframe": "tomorrow"}, model_name="test-model")
        assert res == "MOCK_SCENARIO_RESULT"
