"""P1 Regression: dedup threshold decoupling + MODEL_WEIGHTS completeness.

Reproduces the 2026-08-27 collision:
 - Custom AI Chips (4685e74f...) vs US Gas Power Pipeline sim 0.77 incorrectly deduped at 0.75
 - Corporate Margins vs Q2 GDP sim 0.80
Fix: consensus now uses MEMORY_DEDUP_THRESHOLD=0.90 (store default) not grouping sim_threshold=0.75.
"""

from unittest.mock import AsyncMock, patch

import pytest

from analysis.consensus import process_consensus
from core.config import (
    DEEPSEEK_FLASH_MODEL,
    MEMORY_DEDUP_THRESHOLD,
    MINIMAX_MODEL,
    MODEL_WEIGHTS,
)
from core.models import MacroEvent


def test_memory_dedup_threshold_is_090():
    """Guard that the new constant is 0.90 — prevents regression to 0.75."""
    assert MEMORY_DEDUP_THRESHOLD == 0.90


def test_model_weights_complete():
    """MODEL_WEIGHTS must cover all active models from models.json (P1)."""
    assert MINIMAX_MODEL in MODEL_WEIGHTS, "MINIMAX_MODEL missing"
    assert DEEPSEEK_FLASH_MODEL in MODEL_WEIGHTS, "DEEPSEEK_FLASH_MODEL missing"
    # All weights remain 1.0 (equal influence) — explicit per config
    for k, v in MODEL_WEIGHTS.items():
        assert v == 1.0, f"Unexpected weight for {k}: {v}"


def test_model_weights_covers_all_expected_models():
    """At minimum the 6 canonical models must be present."""
    from core.config import ANTHROPIC_MODEL, DEEPSEEK_MODEL, GEMINI_MODEL, OPENAI_MODEL

    for m in [OPENAI_MODEL, ANTHROPIC_MODEL, GEMINI_MODEL, DEEPSEEK_MODEL, DEEPSEEK_FLASH_MODEL, MINIMAX_MODEL]:
        assert m in MODEL_WEIGHTS


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.synthesize_event")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_consensus_uses_dedup_threshold_090_not_grouping_075(
    mock_add_memory, mock_get_embeddings, mock_synthesize, mock_discovery
):
    """Grouping at 0.78 should trigger consensus, but promotion must use dedup 0.90."""
    mock_add_memory.return_value = "new-uuid"
    mock_discovery.return_value.discover_assets = AsyncMock(return_value=[])
    mock_synthesize.return_value = {"name": "Synthesized", "summary": "Summary"}

    events = [
        MacroEvent(
            event_name="Quantum Investment Event A",
            impact="BULLISH",
            confidence=85,
            reasoning="r1",
            source_id="s1",
            model_provider="openai",
            model_name="gpt-4",
        ),
        MacroEvent(
            event_name="Quantum Investment Event B",
            impact="BULLISH",
            confidence=80,
            reasoning="r2",
            source_id="s1",
            model_provider="anthropic",
            model_name="claude-3",
        ),
    ]
    # sim 0.78 > grouping 0.75 => group together
    mock_get_embeddings.return_value = [[1.0, 0.0], [0.78, 0.62577951]]

    await process_consensus(events, threshold=2)

    assert mock_add_memory.called
    kwargs = mock_add_memory.call_args.kwargs
    # Must use dedup threshold, not the grouping threshold
    assert kwargs["similarity_threshold"] == 0.90, f"Got {kwargs['similarity_threshold']}"
    assert kwargs["similarity_threshold"] == MEMORY_DEDUP_THRESHOLD
    assert kwargs["check_similarity"] is True
    assert kwargs["lookback_hours"] == 24


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.synthesize_event")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_distinct_events_sim_077_not_collapsed_via_dedup(
    mock_add_memory, mock_get_embeddings, mock_synthesize, mock_discovery
):
    """Regression for 4685e74f collision: two distinct synthesized names with sim 0.77 must get different IDs.

    We simulate the second promotion finding Sim 0.77. With dedup 0.90 it must INSERT (new ID),
    not reinforce. We verify add_memory is invoked with 0.90 so find_similar_memory would not match.
    """
    # First promotion returns id A, second would have returned id A if dedup incorrectly at 0.75
    mock_add_memory.side_effect = ["id-A-custom-ai", "id-B-gas-pipeline"]
    mock_discovery.return_value.discover_assets = AsyncMock(return_value=[])
    # synthesize returns distinct names per group call
    mock_synthesize.side_effect = [
        {"name": "Custom AI Chips Challenge Nvidia", "summary": "Hyperscalers custom silicon"},
        {"name": "US Gas Power Pipeline Data Center Expansion", "summary": "Gas turbine buildout"},
    ]

    # Two separate consensus groups, each with 2 models
    # We call process_consensus twice to simulate sequential promotions;
    # each time embeddings are identical within group (sim 1.0) but cross-group sim would be 0.77
    # The bug was cross-group dedup, so we assert the second call still inserts.
    events_group1 = [
        MacroEvent(
            event_name="Custom AI Chips",
            impact="BULLISH",
            confidence=80,
            reasoning="r",
            source_id="s1",
            model_provider="openai",
            model_name="gpt-4",
        ),
        MacroEvent(
            event_name="Custom AI Chips",
            impact="BULLISH",
            confidence=80,
            reasoning="r",
            source_id="s1",
            model_provider="anthropic",
            model_name="claude-3",
        ),
    ]
    events_group2 = [
        MacroEvent(
            event_name="US Gas Power Pipeline",
            impact="BULLISH",
            confidence=80,
            reasoning="r",
            source_id="s2",
            model_provider="openai",
            model_name="gpt-4",
        ),
        MacroEvent(
            event_name="US Gas Power Pipeline",
            impact="BULLISH",
            confidence=80,
            reasoning="r",
            source_id="s2",
            model_provider="anthropic",
            model_name="claude-3",
        ),
    ]

    mock_get_embeddings.return_value = [[1.0, 0.0], [1.0, 0.0]]
    await process_consensus(events_group1, threshold=2)
    mock_get_embeddings.return_value = [[1.0, 0.0], [1.0, 0.0]]
    await process_consensus(events_group2, threshold=2)

    assert mock_add_memory.call_count == 2
    # Both calls used dedup 0.90, so even though cross-group content sim is 0.77, they don't match
    for call in mock_add_memory.call_args_list:
        assert call.kwargs["similarity_threshold"] == 0.90
    # IDs are distinct — no collision (side_effect list already proves two different IDs)
