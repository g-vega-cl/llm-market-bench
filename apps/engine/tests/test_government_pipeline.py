"""Tests for the Government Ingestion Pipeline."""

from unittest.mock import MagicMock, patch

import pytest

from core.models import DecisionsResponse, MacroEvent
from ingest.government import GovernmentPipeline


@pytest.mark.asyncio
async def test_government_pipeline_await_crash():
    """Test that GovernmentPipeline.run() works without raising a TypeError from awaiting the Gemini call."""
    mock_client = MagicMock()
    mock_supabase = MagicMock()

    # Mock Gemini client chat.completions.create return value
    # If the client is synchronous, create() returns a DecisionsResponse.
    # If it is async, it returns a coroutine. Let's start with a synchronous return
    # to reproduce the TypeErrors that occur when awaiting a sync return.
    mock_response = DecisionsResponse(
        decisions=[],
        macro_events=[
            MacroEvent(
                event_name="Test Policy",
                impact="BULLISH",
                confidence=80,
                reasoning="Test policy reasoning",
                source_id="test_src",
            )
        ],
    )
    mock_client.chat.completions.create.return_value = mock_response

    with (
        patch("ingest.government.get_gemini_client", return_value=mock_client),
        patch("ingest.government.get_supabase_client", return_value=mock_supabase),
        patch("ingest.government.add_memory", return_value="some-uuid") as mock_add_memory,
    ):
        pipeline = GovernmentPipeline()
        count = await pipeline.run()

        assert count == 1
        mock_add_memory.assert_called_once()
        assert "Test Policy" in mock_add_memory.call_args[1]["content"]
