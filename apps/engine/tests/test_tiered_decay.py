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

    # LESSON_LEARNED, POST_MORTEM, ACADEMIC_PAPER → never decay (skipped)
    # UNCROWDED_TRADE → slow decay (0.72/month), now included
    assert len(update_calls) == 3, (
        f"Expected 3 updates (MARKET_EVENT, GOVERNMENT_INCENTIVE, UNCROWDED_TRADE). Got: "
        f"{[c[0][0] for c in update_calls]}"
    )

    payloads = [call[0][0] for call in update_calls]
    assert {"relevance_score": 0.5} in payloads   # MARKET_EVENT: 50% per month
    assert {"relevance_score": 0.75} in payloads  # GOVERNMENT_INCENTIVE: 25% per month
    assert {"relevance_score": 0.72} in payloads  # UNCROWDED_TRADE: 28% per month


def test_uncrowded_trade_decay_timeline():
    """Documents the intended decay timeline for UNCROWDED_TRADE memories.

    Design targets (half-life = 30 days, threshold = 0.05):
    - Still meaningful at 2 months (> 0.3 relevance)
    - Below retrieval threshold by 12 months (< 0.05)
    """
    DECAY_FACTOR = 0.72
    THRESHOLD = 0.05

    relevance = 1.0
    months_until_gone = None
    for month in range(1, 25):
        relevance *= DECAY_FACTOR
        if relevance < THRESHOLD and months_until_gone is None:
            months_until_gone = month

    assert relevance < THRESHOLD, "Should be well below threshold after 24 months"
    assert months_until_gone is not None, "Should eventually decay below threshold"
    assert months_until_gone <= 12, f"Should be gone by month 12, but took {months_until_gone} months"

    # Verify 2-month relevance directly
    two_month_relevance = 1.0 * (DECAY_FACTOR**2)
    assert two_month_relevance > 0.3, (
        f"2-month relevance {two_month_relevance:.3f} is too low — thesis fades too fast"
    )
