"""Tests for the Event Consensus Protocol."""

from unittest.mock import AsyncMock, patch

import pytest

from analysis.consensus import _is_vague_government_event, _resolve_impact_tie, process_consensus
from core.config import GEMINI_MODEL
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
        MacroEvent(
            event_name="AI Boom",
            impact="BULLISH",
            confidence=95,
            reasoning="NVIDIA earnings validate thesis",
            source_id="source2",
            model_provider="openai",
            model_name="gpt-4",
        ),
        MacroEvent(
            event_name="Crypto Crash",
            impact="BEARISH",
            confidence=70,
            reasoning="Regulatory pressure increasing",
            source_id="source3",
            model_provider="gemini",
            model_name=GEMINI_MODEL,
        ),
    ]


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.synthesize_event")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_reaches_consensus(
    mock_add_memory, mock_get_embeddings, mock_synthesize, mock_discovery, sample_events
):
    # Mock return values
    mock_add_memory.return_value = "new-uuid"
    mock_discovery.return_value.discover_assets = AsyncMock(return_value=[])
    mock_synthesize.return_value = {
        "name": "Synthesized Event",
        "summary": "Synthesized Summary",
        "future_date": "June 2026",
    }

    # Mock embeddings: 0 and 1 are same (Fed), 2 and 3 are different
    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0],  # Fed
        [1.0, 0.0, 0.0],  # Fed
        [0.0, 1.0, 0.0],  # AI Boom
        [0.0, 0.0, 1.0],  # Crypto Crash
    ]

    # Process with threshold of 2
    consensus_events = await process_consensus(sample_events, threshold=2)

    # Assertions
    assert len(consensus_events) == 1
    assert consensus_events[0]["event_name"] == "Synthesized Event"
    assert len(consensus_events[0]["models_involved"]) == 2  # openai_gpt-4 and anthropic_claude-3

    # Verify add_memory was called with target_date
    mock_add_memory.assert_called_once()
    kwargs = mock_add_memory.call_args.kwargs
    assert kwargs["target_date"] == "June 2026"


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.synthesize_event")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_with_date_note(
    mock_add_memory, mock_get_embeddings, mock_synthesize, mock_discovery, sample_events
):
    mock_add_memory.return_value = "new-uuid"
    mock_discovery.return_value.discover_assets = AsyncMock(return_value=[])
    mock_synthesize.return_value = {
        "name": "Tentative Event",
        "summary": "Tentative Summary",
        "future_date": "2026-02-21",
        "future_date_note": "tentative",
    }

    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]

    await process_consensus(sample_events, threshold=2)

    mock_add_memory.assert_called_once()
    kwargs = mock_add_memory.call_args.kwargs
    assert kwargs["target_date"] == "2026-02-21"
    assert kwargs["metadata"]["future_date_note"] == "tentative"


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.synthesize_event")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_deduplication(
    mock_add_memory, mock_get_embeddings, mock_synthesize, mock_discovery, sample_events
):
    mock_add_memory.return_value = None  # Simulate deduplication (returns None if skip)
    mock_discovery.return_value.discover_assets = AsyncMock(return_value=[])
    mock_synthesize.return_value = {
        "name": "Fed Rate Hike",
        "summary": "The Fed is likely to hike rates soon due to persistent inflation.",
        "scenario_analysis": "Outcome A: Fed hikes by 25bps. Trading Plan: Long USD.",
    }

    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]

    consensus_events = await process_consensus(sample_events, threshold=2)

    # Threshold met but deduplicated
    assert len(consensus_events) == 0
    assert mock_add_memory.called


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_no_consensus(mock_add_memory, mock_get_embeddings, mock_discovery, sample_events):
    mock_add_memory.return_value = "new-id"
    mock_discovery.return_value.discover_assets = AsyncMock(return_value=[])

    # All different
    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.1, 0.9],
        [0.5, 0.5, 0.0],
    ]

    # Process with threshold of 2
    consensus_events = await process_consensus(sample_events, threshold=2)

    # Assertions
    assert len(consensus_events) == 0
    assert not mock_add_memory.called


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.synthesize_event")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_semantic_grouping(
    mock_add_memory, mock_get_embeddings, mock_synthesize, mock_discovery, sample_events
):
    mock_add_memory.return_value = "new-id"
    mock_discovery.return_value.discover_assets = AsyncMock(return_value=[])
    mock_synthesize.return_value = {"name": "Semantic Synthesized", "summary": "Semantic Summary"}

    # Mock embeddings for semantic similarity
    # Event 0: Fed Rate Hike
    # Event 1: Fed Rate Hike (same)
    # Let's add Event 4: "Interest Rate Increase" from a 3rd model
    events = sample_events + [
        MacroEvent(
            event_name="Interest Rate Increase",
            impact="BEARISH",
            confidence=80,
            reasoning="Market expecting higher rates",
            source_id="source1",
            model_provider="gemini",
            model_name=GEMINI_MODEL,
        )
    ]

    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.95, 0.05, 0.0],
    ]

    consensus_events = await process_consensus(events, threshold=3)

    assert len(consensus_events) == 1
    assert consensus_events[0]["event_name"] == "Semantic Synthesized"
    assert len(consensus_events[0]["models_involved"]) == 3
    assert mock_add_memory.called


# --- Tests for _resolve_impact_tie helper ---


def test_resolve_impact_tie_clear_winner():
    """Test that a clear winner is returned when one impact has most votes."""
    impact_counts = {"BULLISH": 3, "BEARISH": 1, "NEUTRAL": 1}
    assert _resolve_impact_tie(impact_counts) == "BULLISH"


def test_resolve_impact_tie_returns_neutral_on_tie():
    """Test that NEUTRAL is returned when BULLISH and BEARISH are tied."""
    impact_counts = {"BULLISH": 2, "BEARISH": 2}
    assert _resolve_impact_tie(impact_counts) == "NEUTRAL"


def test_resolve_impact_tie_prefers_neutral_in_three_way_tie():
    """Test that NEUTRAL is preferred when all three impacts are tied."""
    impact_counts = {"BULLISH": 2, "BEARISH": 2, "NEUTRAL": 2}
    assert _resolve_impact_tie(impact_counts) == "NEUTRAL"


def test_resolve_impact_tie_empty_dict():
    """Test that NEUTRAL is returned for empty impact counts."""
    assert _resolve_impact_tie({}) == "NEUTRAL"


def test_resolve_impact_tie_single_impact():
    """Test that the single impact is returned when only one exists."""
    assert _resolve_impact_tie({"BEARISH": 5}) == "BEARISH"


# --- Tests for vague government event rejection gate ---

_VAGUE_GOV_NAMES = [
    "Ongoing Legislative Policy Developments",
    "Government Policy Update",
    "Government Policy Structural Update",
    "Policy Structural Update",
    "Ongoing Policy Developments",
    "VAGUE_GOVERNMENT_EVENT",
]

_SPECIFIC_GOV_NAMES = [
    "US Farm Bill 2026 Agri-Tech Push",
    "CHIPS Act Expansion",
    "EU Green Hydrogen Act",
    "Japan GX Transformation Bonds",
    "Fed Rate Cut Cycle",
]

_NON_POLICY_NAMES = [
    "AI Demand Surge",
    "Earnings Season Begins",
    "Oil Supply Disruption",
    "Crypto Crash",
]


@pytest.mark.parametrize("name", _VAGUE_GOV_NAMES)
def test_is_vague_government_event_true_for_generic_names(name):
    assert _is_vague_government_event(name) is True, f"'{name}' should be vague"


@pytest.mark.parametrize("name", _SPECIFIC_GOV_NAMES)
def test_is_vague_government_event_false_for_specific_names(name):
    assert _is_vague_government_event(name) is False, f"'{name}' should not be vague"


@pytest.mark.parametrize("name", _NON_POLICY_NAMES)
def test_is_vague_government_event_false_for_non_policy_events(name):
    assert _is_vague_government_event(name) is False, f"'{name}' should not be flagged"


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.synthesize_event")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_rejects_vague_government_event(
    mock_add_memory, mock_get_embeddings, mock_synthesize, mock_discovery
):
    """When the synthesizer returns a vague government event name, the consensus
    pipeline should reject it and NOT promote it to memory."""
    mock_add_memory.return_value = "new-uuid"
    mock_discovery.return_value.discover_assets = AsyncMock(return_value=[])
    mock_synthesize.return_value = {
        "name": "Ongoing Legislative Policy Developments",
        "summary": "The market is monitoring ongoing legislative and government policy developments.",
    }

    events = [
        MacroEvent(
            event_name="Government Policy Update",
            impact="NEUTRAL",
            confidence=60,
            reasoning="Policy changes may affect markets.",
            source_id="source1",
            model_provider="openai",
            model_name="gpt-4",
        ),
        MacroEvent(
            event_name="Government Policy Update",
            impact="NEUTRAL",
            confidence=55,
            reasoning="Government legislation is pending.",
            source_id="source1",
            model_provider="anthropic",
            model_name="claude-3",
        ),
        MacroEvent(
            event_name="Government Policy Update",
            impact="NEUTRAL",
            confidence=50,
            reasoning="Policy developments ongoing.",
            source_id="source1",
            model_provider="gemini",
            model_name=GEMINI_MODEL,
        ),
    ]

    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
    ]

    consensus_events = await process_consensus(events, threshold=2)

    assert len(consensus_events) == 0
    mock_add_memory.assert_not_called()


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.synthesize_event")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_accepts_specific_government_event(
    mock_add_memory, mock_get_embeddings, mock_synthesize, mock_discovery
):
    """When the synthesizer returns a specific government event name, the pipeline
    should accept and promote it to memory normally."""
    mock_add_memory.return_value = "new-uuid"
    mock_discovery.return_value.discover_assets = AsyncMock(return_value=[])
    mock_synthesize.return_value = {
        "name": "US Farm Bill 2026",
        "summary": "Congress advances the Farm, Food and National Security Act with $50B for precision agriculture.",
        "scenario_analysis": "Scenario A: Passage -> Trading Plan: Buy DE.\nScenario B: Stalled -> Trading Plan: Hold.",
    }

    events = [
        MacroEvent(
            event_name="US Farm Bill 2026",
            impact="BULLISH",
            confidence=85,
            reasoning="Farm bill advancing through Congress.",
            source_id="source1",
            model_provider="openai",
            model_name="gpt-4",
        ),
        MacroEvent(
            event_name="US Farm Bill 2026",
            impact="BULLISH",
            confidence=80,
            reasoning="Ag subsidies boost expected.",
            source_id="source1",
            model_provider="anthropic",
            model_name="claude-3",
        ),
    ]

    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
    ]

    consensus_events = await process_consensus(events, threshold=2)

    assert len(consensus_events) == 1
    assert consensus_events[0]["event_name"] == "US Farm Bill 2026"
    mock_add_memory.assert_called_once()
