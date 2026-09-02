"""Tests for ingest.calendar module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import DecisionsResponse, MacroEvent
from ingest.calendar import CalendarPipeline

SAMPLE_HTML = """
<table id="calendar">
    <tr>
        <th colspan="6">Wednesday March 11 2026</th>
    </tr>
    <tr data-event="CPI" data-country="united states">
        <td>10:00 AM</td>
        <td>USA</td>
        <td>CPI Data</td>
        <td>3.2%</td>
        <td>3.1%</td>
        <td>3.0%</td>
    </tr>
</table>
"""

REALISTIC_TE_HTML = """
<table id="calendar">
    <tr>
        <th colspan="6">Wednesday September 02 2026</th>
    </tr>
    <tr data-url="/australia/gdp-growth" data-id="401396" data-country="australia" data-category="gdp growth rate" data-event="gdp growth rate qoq" data-symbol="AUNAGDPC">
        <td class="2026-09-02" style="white-space: nowrap;">
            <span class="event-0 calendar-date-3">01:30 AM</span>
        </td>
        <td class="calendar-item" style="white-space: nowrap">
            <table style="padding: 0px;">
                <tr>
                    <td style="padding-left: 5px;"><div class="flag flag-au" title="Australia"></div></td>
                    <td class="calendar-iso" style="padding-left: 5px;" title="Australia">AU</td>
                </tr>
            </table>
        </td>
        <td style="max-width: 250px; overflow-x: hidden;">
            <a class="calendar-event" href="/australia/gdp-growth">GDP Growth Rate QoQ</a> <span class="calendar-reference">Q2</span>
        </td>
        <td class="calendar-item calendar-item-positive">
            <a href="/australia/gdp-growth"><span id="actual">0.4%</span></a>
        </td>
        <td class="calendar-item calendar-item-positive">
            <span id="previous">0.3%</span>
        </td>
        <td class="calendar-item calendar-item-positive">
            <a id="consensus">0.3%</a>
        </td>
        <td class="calendar-item calendar-item-positive">
            <a id="forecast">0.2%</a>
        </td>
        <td class="d-md-none d-lg-table-cell"></td>
        <td class="d-none d-md-table-cell d-lg-none"></td>
        <td class="td-alert"></td>
    </tr>
</table>
"""


@pytest.fixture
def pipeline():
    with (
        patch("ingest.calendar.get_deepseek_client") as mock_get_client,
        patch("ingest.calendar.get_supabase_client") as mock_get_sb,
    ):
        mock_get_client.return_value = MagicMock()
        mock_get_sb.return_value = MagicMock()
        return CalendarPipeline()


def test_parse_events_simple_fallback(pipeline):
    """Test parsing of simple 6-column HTML table."""
    events = pipeline.parse_events(SAMPLE_HTML)

    assert len(events) == 1
    assert events[0]["date"] == "2026-03-11"
    assert events[0]["country"] == "United States"
    assert events[0]["event"] == "CPI Data"
    assert events[0]["actual"] == "3.2%"


def test_parse_events_realistic_nested_html(pipeline):
    """Test parsing of realistic TradingEconomics HTML with nested country table."""
    events = pipeline.parse_events(REALISTIC_TE_HTML)

    assert len(events) == 1
    assert events[0]["date"] == "2026-09-02"
    assert events[0]["time"] == "01:30 AM"
    assert events[0]["country"] == "Australia"
    assert "GDP Growth Rate QoQ" in events[0]["event"]
    assert events[0]["actual"] == "0.4%"
    assert events[0]["previous"] == "0.3%"
    assert events[0]["consensus"] == "0.3%"
    assert events[0]["forecast"] == "0.2%"


@pytest.mark.asyncio
async def test_run_calendar_pipeline_deterministic_source_id(pipeline):
    """Test the pipeline run with deterministic [#N] source_id indexing."""
    with (
        patch.object(pipeline, "fetch_html", return_value=REALISTIC_TE_HTML),
        patch.object(pipeline.client.chat.completions, "create", new_callable=AsyncMock) as mock_deepseek,
        patch("ingest.calendar.add_memory") as mock_add_memory,
    ):
        mock_res = DecisionsResponse(
            macro_events=[
                MacroEvent(
                    event_name="Australian GDP Growth Print",
                    impact="BULLISH",
                    importance_score=9,
                    reasoning="Australian growth beat expectations.",
                    target_date="2026-09-02",
                    confidence=95,
                    source_id="[#0]",
                )
            ]
        )
        mock_deepseek.return_value = mock_res
        mock_add_memory.return_value = "mem_id_123"

        count = await pipeline.run()

        assert count == 1
        mock_add_memory.assert_called_once()
        args, kwargs = mock_add_memory.call_args
        assert kwargs["memory_type"] == "CALENDAR_EVENT"
        assert kwargs["importance_score"] == 9
        assert kwargs["target_date"] == "2026-09-02"
        assert kwargs["check_similarity"] is True
        assert "(01:30 AM)" in kwargs["content"]
        assert "2026-09-02" in kwargs["content"]
        assert kwargs["metadata"]["is_future_catalyst"] is True
        assert kwargs["metadata"]["event_time"] == "01:30 AM"
        assert kwargs["metadata"]["country"] == "Australia"


@pytest.mark.asyncio
async def test_run_calendar_pipeline_low_importance(pipeline):
    """Test that low importance events are not added to memories."""
    with (
        patch.object(pipeline, "fetch_html", return_value=SAMPLE_HTML),
        patch.object(pipeline.client.chat.completions, "create", new_callable=AsyncMock) as mock_deepseek,
        patch("ingest.calendar.add_memory") as mock_add_memory,
    ):
        mock_res = DecisionsResponse(
            macro_events=[
                MacroEvent(
                    event_name="Minor Data",
                    impact="NEUTRAL",
                    importance_score=5,
                    reasoning="Not very important.",
                    target_date="2026-03-11",
                    confidence=80,
                    source_id="2026-03-11",
                )
            ]
        )
        mock_deepseek.return_value = mock_res

        count = await pipeline.run()

        assert count == 0
        mock_add_memory.assert_not_called()

