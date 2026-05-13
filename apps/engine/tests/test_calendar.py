"""Tests for ingest.calendar module."""

from unittest.mock import MagicMock, patch

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

@pytest.fixture
def pipeline():
    with patch("ingest.calendar.get_deepseek_client") as mock_get_client, \
         patch("ingest.calendar.get_supabase_client") as mock_get_sb:
        mock_get_client.return_value = MagicMock()
        mock_get_sb.return_value = MagicMock()
        return CalendarPipeline()

def test_parse_events(pipeline):
    """Test parsing of Trading Economics HTML."""
    events = pipeline.parse_events(SAMPLE_HTML)
    
    assert len(events) == 1
    assert events[0]["date"] == "2026-03-11"
    assert events[0]["country"] == "United States"
    assert events[0]["event"] == "CPI"
    assert events[0]["actual"] == "3.2%"

@pytest.mark.asyncio
async def test_run_calendar_pipeline_success(pipeline):
    """Test the full pipeline run with mocked fetch and DeepSeek."""
    from unittest.mock import AsyncMock
    with patch.object(pipeline, "fetch_html", return_value=SAMPLE_HTML), \
         patch.object(pipeline.client.chat.completions, "create", new_callable=AsyncMock) as mock_deepseek, \
         patch("ingest.calendar.add_memory") as mock_add_memory:

        # Mock DeepSeek response
        mock_res = DecisionsResponse(
            macro_events=[
                MacroEvent(
                    event_name="US CPI Data Release",
                    impact="BEARISH",
                    importance_score=9,
                    reasoning="Higher than expected inflation might lead to rate hikes.",
                    expiry_date="2026-03-11",
                    confidence=95,
                    source_id="2026-03-11"
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
        assert kwargs["target_date"] == "2026-03-11"
        assert kwargs["check_similarity"] is True
        
        # New assertions for time and future catalyst
        assert "(10:00 AM)" in kwargs["content"]
        assert kwargs["metadata"]["is_future_catalyst"] is True
        assert kwargs["metadata"]["event_time"] == "10:00 AM"

@pytest.mark.asyncio
async def test_run_calendar_pipeline_low_importance(pipeline):
    """Test that low importance events are not added to memories."""
    from unittest.mock import AsyncMock
    with patch.object(pipeline, "fetch_html", return_value=SAMPLE_HTML), \
         patch.object(pipeline.client.chat.completions, "create", new_callable=AsyncMock) as mock_deepseek, \
         patch("ingest.calendar.add_memory") as mock_add_memory:

        # Mock DeepSeek response with low importance
        mock_res = DecisionsResponse(
            macro_events=[
                MacroEvent(
                    event_name="Minor Data",
                    impact="NEUTRAL",
                    importance_score=5,
                    reasoning="Not very important.",
                    expiry_date="2026-03-11",
                    confidence=80,
                    source_id="2026-03-11"
                )
            ]
        )
        mock_deepseek.return_value = mock_res

        count = await pipeline.run()

        assert count == 0
        mock_add_memory.assert_not_called()
