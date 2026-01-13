"""Tests for the Event Consensus Protocol."""

import pytest
from unittest.mock import MagicMock, patch

from core.models import MacroEvent
from consensus import process_consensus

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
            model_name="gpt-4"
        ),
        MacroEvent(
            event_name="Fed Rate Hike",
            impact="BEARISH",
            confidence=85,
            reasoning="Inflation remains high, expecting hike",
            source_id="source1",
            model_provider="anthropic",
            model_name="claude-3"
        ),
        MacroEvent(
            event_name="AI Boom",
            impact="BULLISH",
            confidence=95,
            reasoning="NVIDIA earnings validate thesis",
            source_id="source2",
            model_provider="openai",
            model_name="gpt-4"
        ),
        MacroEvent(
            event_name="Crypto Crash",
            impact="BEARISH",
            confidence=70,
            reasoning="Regulatory pressure increasing",
            source_id="source3",
            model_provider="gemini",
            model_name="gemini-1.5"
        )
    ]

@patch("consensus.check_recent_memories")
@patch("consensus.synthesize_event")
@patch("consensus.get_embeddings_batch")
@patch("consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_reaches_consensus(mock_add_memory, mock_get_embeddings, mock_synthesize, mock_check_recent, sample_events):
    # Set up mock return values
    mock_add_memory.return_value = True
    mock_check_recent.return_value = False
    mock_synthesize.return_value = {"name": "Synthesized Event", "summary": "Synthesized Summary"}
    
    # Mock embeddings: 0 and 1 are same (Fed), 2 and 3 are different
    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0], # Fed
        [1.0, 0.0, 0.0], # Fed
        [0.0, 1.0, 0.0], # AI Boom
        [0.0, 0.0, 1.0], # Crypto Crash
    ]
    
    # Process with threshold of 2
    consensus_events = await process_consensus(sample_events, threshold=2)
    
    # Assertions
    assert len(consensus_events) == 1
    assert consensus_events[0]["event_name"] == "Synthesized Event"
    assert len(consensus_events[0]["models_involved"]) == 2 # openai_gpt-4 and anthropic_claude-3
    assert mock_add_memory.called

@patch("consensus.check_recent_memories")
@patch("consensus.synthesize_event")
@patch("consensus.get_embeddings_batch")
@patch("consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_deduplication(mock_add_memory, mock_get_embeddings, mock_synthesize, mock_check_recent, sample_events):
    mock_add_memory.return_value = True
    mock_check_recent.return_value = True # Simulate recent similar event found
    
    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
    
    consensus_events = await process_consensus(sample_events, threshold=2)
    
    # Threshold met but deduplicated
    assert len(consensus_events) == 0
    assert not mock_add_memory.called
    assert not mock_synthesize.called

@patch("consensus.check_recent_memories")
@patch("consensus.get_embeddings_batch")
@patch("consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_no_consensus(mock_add_memory, mock_get_embeddings, mock_check_recent, sample_events):
    mock_add_memory.return_value = True
    mock_check_recent.return_value = False
    
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

@patch("consensus.check_recent_memories")
@patch("consensus.synthesize_event")
@patch("consensus.get_embeddings_batch")
@patch("consensus.add_memory")
@pytest.mark.asyncio
async def test_process_consensus_semantic_grouping(mock_add_memory, mock_get_embeddings, mock_synthesize, mock_check_recent, sample_events):
    mock_add_memory.return_value = True
    mock_check_recent.return_value = False
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
            model_name="gemini-1.5"
        )
    ]
    
    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.95, 0.05, 0.0]
    ]
    
    consensus_events = await process_consensus(events, threshold=3)
    
    assert len(consensus_events) == 1
    assert consensus_events[0]["event_name"] == "Semantic Synthesized"
    assert len(consensus_events[0]["models_involved"]) == 3
    assert mock_add_memory.called
