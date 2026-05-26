"""Tests for the Event Consensus Protocol resilience to API failures."""

from unittest.mock import AsyncMock, patch

import pytest

from analysis.consensus import process_consensus
from core.models import MacroEvent


@pytest.fixture
def sample_events():
    return [
        MacroEvent(
            event_name="Fed Rate Hike",
            impact="BEARISH",
            confidence=90,
            reasoning="Fed signaled aggressive stance",
            source_id="source1",
            model_provider="openai",
            model_name="gpt-4",
        ),
        MacroEvent(
            event_name="Fed Rate Hike",
            impact="BEARISH",
            confidence=85,
            reasoning="Inflation remains high, expecting hike",
            source_id="source1",
            model_provider="anthropic",
            model_name="claude-3",
        ),
    ]


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.synthesize_event")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_handles_api_failure_gracefully(
    mock_add_memory, mock_get_embeddings, mock_synthesize, mock_discovery, sample_events
):
    """Verifies that if the embeddings batch generator returns an empty list
    (e.g., due to an API 429 rate limit or connection failure),
    the consensus protocol does not crash with IndexError and instead falls back
    to exact string comparison grouping.
    """
    # Mock embeddings returning empty (as in 429 failure)
    mock_get_embeddings.return_value = []

    mock_add_memory.return_value = "new-uuid"
    mock_discovery.return_value.discover_assets = AsyncMock(return_value=[])
    mock_synthesize.return_value = {
        "name": "Synthesized Event",
        "summary": "Synthesized Summary",
        "future_date": "June 2026",
    }

    # Under the bug, this throws IndexError: list index out of range.
    # With the fix, it should complete successfully using the exact string match fallback.
    consensus_events = await process_consensus(sample_events, threshold=2)

    assert len(consensus_events) == 1
    assert consensus_events[0]["event_name"] == "Synthesized Event"
    mock_add_memory.assert_called_once()


@patch("memory.embeddings.get_client")
def test_get_embeddings_batch_retries_on_failure(mock_get_client):
    """Verifies that get_embeddings_batch retries transient failures
    using exponential backoff via tenacity, eventually succeeding.
    """
    from unittest.mock import MagicMock

    from memory.embeddings import get_embeddings_batch

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_response = MagicMock()
    mock_emb = MagicMock()
    mock_emb.values = [0.1] * 768
    mock_response.embeddings = [mock_emb]

    # We raise an Exception on the first 2 calls and succeed on the 3rd
    mock_client.models.embed_content.side_effect = [
        Exception("Rate limit exceeded"),
        Exception("Rate limit exceeded"),
        mock_response,
    ]

    results = get_embeddings_batch(["test text"])

    assert len(results) == 1
    assert results[0] == [0.1] * 768
    assert mock_client.models.embed_content.call_count == 3
