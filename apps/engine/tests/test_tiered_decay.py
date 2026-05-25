"""Tests for adaptive tiered memory decay."""

from unittest.mock import MagicMock, patch

import pytest
from apps.engine.memory.store import decay_memories


@pytest.fixture
def mock_supabase():
    with patch("apps.engine.memory.store.get_supabase_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_tiered_decay_applies_correct_rates(mock_supabase):
    # Mock responses representing different memory types
    memories = [
        {"id": "m1", "memory_type": "MARKET_EVENT", "relevance_score": 1.0},
        {"id": "m2", "memory_type": "GOVERNMENT_INCENTIVE", "relevance_score": 1.0},
        {"id": "m3", "memory_type": "LESSON_LEARNED", "relevance_score": 1.0},
        {"id": "m4", "memory_type": "UNCROWDED_TRADE", "relevance_score": 1.0},
        {"id": "m5", "memory_type": "POST_MORTEM", "relevance_score": 1.0},
        {"id": "m6", "memory_type": "ACADEMIC_PAPER", "relevance_score": 1.0},
    ]

    # Setup the mock database read chain to return these memories
    mock_select_chain = (
        mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.gt.return_value.execute
    )
    mock_select_chain.return_value = MagicMock(data=memories)

    # Run decay_memories
    decay_memories(mock_supabase, decay_days=30)

    # Capture the updates made
    update_calls = mock_supabase.table.return_value.update.call_args_list
    assert len(update_calls) == 2  # Only MARKET_EVENT and GOVERNMENT_INCENTIVE should be updated

    # A simpler way is to assert the mock_supabase update payloads
    payloads = [call[0][0] for call in update_calls]
    assert {"relevance_score": 0.5} in payloads  # MARKET_EVENT decayed by 50%
    assert {"relevance_score": 0.75} in payloads  # GOVERNMENT_INCENTIVE decayed by 25%
