"""Tests for weekly offline memory consolidation ('sleep' cycle)."""

from unittest.mock import MagicMock, patch

import pytest
from apps.engine.memory.store import consolidate_overlapping_memories


@pytest.fixture
def mock_supabase():
    with patch("apps.engine.memory.store.get_supabase_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_deepseek():
    # Mock deepseek/deepseek-v4-pro client
    with patch("core.llm.get_deepseek_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_cosine():
    try:
        target = "analysis.consensus.cosine_similarity"
        with patch(target) as mock:
            yield mock
    except ImportError:
        target = "apps.engine.analysis.consensus.cosine_similarity"
        with patch(target) as mock:
            yield mock


@pytest.mark.asyncio
async def test_consolidate_overlapping_memories(mock_supabase, mock_deepseek, mock_cosine):
    # Setup mock active memories
    memories = [
        {
            "id": "uuid-1",
            "content": "The Fed cut rates by 25 basis points in May 2026.",
            "embedding": [0.1, 0.2, 0.3],
            "importance_score": 7,
            "memory_type": "MARKET_EVENT",
        },
        {
            "id": "uuid-2",
            "content": "Federal Reserve announced a 25bps interest rate reduction in May 2026.",
            "embedding": [0.11, 0.21, 0.31],
            "importance_score": 6,
            "memory_type": "MARKET_EVENT",
        },
    ]

    # Mock active memory select query chain
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = memories

    # High similarity between the two memories
    mock_cosine.return_value = 0.95

    # Mock DeepSeek / Instructor synthesis response
    mock_response = MagicMock()
    mock_response.headline = "Federal Reserve rate cut of 25bps in May 2026"
    mock_response.summary = (
        "The Federal Reserve lowered interest rates by 25 basis points in May 2026 to support economic stability."
    )
    mock_response.importance_score = 8
    mock_response.memory_type = "MARKET_EVENT"

    # Handle both sync and async return values for instructor call
    async def mock_create(*args, **kwargs):
        return mock_response

    mock_deepseek.chat.completions.create = mock_create

    # Mock inserting the new synthesized memory and updating old ones
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "uuid-consolidated"}]

    # Run consolidation
    await consolidate_overlapping_memories()

    # Verifications:
    # 1. It should update older memories to SUPERSEDED
    update_calls = mock_supabase.table.return_value.update.call_args_list
    assert len(update_calls) >= 2

    statuses_updated = [call[0][0]["status"] for call in update_calls]
    assert "SUPERSEDED" in statuses_updated

    # 2. It should insert the new consolidated memory
    mock_supabase.table.return_value.insert.assert_called_once()
    insert_payload = mock_supabase.table.return_value.insert.call_args[0][0]
    assert insert_payload["status"] == "ACTIVE"
    assert "Federal Reserve rate cut of 25bps in May 2026" in insert_payload["content"]
    assert insert_payload["parent_id"] == "uuid-1" or insert_payload["parent_id"] == "uuid-2"
    assert insert_payload["relationship_type"] == "UPDATE"
    assert "uuid-1" in insert_payload["metadata"]["consolidated_ids"]
