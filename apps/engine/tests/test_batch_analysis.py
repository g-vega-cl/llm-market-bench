"""Tests for batch analysis logic."""

import pytest
from unittest.mock import AsyncMock, patch
from core.models import DecisionObject
#, DecisionsResponse  <-- Need to import if we mock
from analyze import analyze_chunks

@pytest.fixture
def mock_llm_analyze():
    """Mock the llm.analyze_with_provider function."""
    with patch("core.llm.analyze_with_provider", new_callable=AsyncMock) as m:
        yield m

@pytest.fixture
def mock_retrieve_context():
    """Mock the retrieve_context function."""
    with patch("analyze.retrieve_context") as m:
        m.return_value = "Mocked Context"
        yield m

@pytest.mark.asyncio
async def test_analyze_chunks_batch(mock_llm_analyze, mock_retrieve_context):
    """Test that analyze_chunks correctly batches decisions."""
    
    # Mock return value: multiple decisions from a single batch call
    mock_decisions = [
        DecisionObject(
            signal="BUY", confidence=80, reasoning="Bullish news 1", 
            ticker="AAPL", source_id="src_1"
        ),
        DecisionObject(
            signal="SELL", confidence=70, reasoning="Bearish news 2", 
            ticker="GOOGL", source_id="src_2"
        )
    ]
    mock_llm_analyze.return_value = mock_decisions
    
    chunks = [
        {"source_id": "src_1", "content": "AAPL earnings up"},
        {"source_id": "src_2", "content": "GOOGL earnings down"}
    ]
    
    # Run analysis
    results = await analyze_chunks(chunks)
    
    # Verify we got all decisions
    assert len(results) >= 8  # 4 models * 2 decisions each = 8 total
    
    # Verify analyze_with_provider was called 4 times (once per model)
    assert mock_llm_analyze.call_count == 4
    
    # Verify the call arguments (it should receive the full list of chunks)
    call_args = mock_llm_analyze.call_args[1]
    assert call_args["chunks"] == chunks
    # Context should be aggregated (Mocked Context * 2 chunks = repeated, or just once if mocked simply)
    # Our code aggregates: context += f"\n{ctx}"
    # So we expect "\nMocked Context\nMocked Context"
    assert "Mocked Context" in call_args["context"]

    # Verify attribution metadata was attached
    assert results[0].model_provider is not None
    assert results[0].model_name is not None
