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
    """Mock the retrieve_context_batch function."""
    with patch("analyze.retrieve_context_batch") as m:
        m.return_value = ["Mocked Context"]
        yield m

@pytest.fixture
def mock_get_embeddings():
    """Mock the get_embeddings_batch function."""
    with patch("memory.embeddings.get_embeddings_batch") as m:
        m.return_value = [[0.1] * 768]
        yield m

@pytest.mark.asyncio
async def test_analyze_chunks_batch(mock_llm_analyze, mock_retrieve_context, mock_get_embeddings):
    """Test that analyze_chunks correctly batches decisions."""
    
    from unittest.mock import MagicMock, patch
    
    # Mock return value: multiple decisions from a single batch call
    mock_decisions = [
        DecisionObject(
            signal="BUY", confidence=80, reasoning="Bullish news 1", 
                ticker="AAPL", source_id="src_1",
                is_priced_in=False, is_priced_in_reasoning="News just broke",
                profit_potential_reasoning="First mover advantage",
                strategy_reasoning="Buy AAPL for long term",
                advance_planning_notes="Plan to hold"
        ),
        DecisionObject(
            signal="SELL", confidence=70, reasoning="Bearish news 2", 
                ticker="GOOGL", source_id="src_2",
                is_priced_in=True, is_priced_in_reasoning="Already spiked",
                profit_potential_reasoning="Exit before further drop",
                strategy_reasoning="Sell GOOGL now",
                advance_planning_notes="Move to cash"
        )
    ]
    from core.models import DecisionsResponse
    mock_llm_analyze.return_value = DecisionsResponse(
        decisions=mock_decisions,
        macro_events=[]
    )
    
    chunks = [
        {"source_id": "src_1", "content": "AAPL earnings up"},
        {"source_id": "src_2", "content": "GOOGL earnings down"}
    ]
    
    # Mock Portfolio and MarketDataManager to avoid Supabase dependency
    with patch("analyze.Portfolio") as mock_portfolio_class, \
         patch("analyze.MarketDataManager") as mock_market_data_class:
        
        from unittest.mock import AsyncMock
        mock_portfolio = MagicMock()
        mock_portfolio.positions = {}
        mock_portfolio.initialize = AsyncMock(return_value=None)
        mock_portfolio.calculate_reg_t_metrics = MagicMock()
        mock_portfolio.save_metrics = AsyncMock(return_value=None)
        mock_portfolio.get_portfolio_summary = MagicMock(return_value="Portfolio: $10,000 cash")
        mock_portfolio_class.return_value = mock_portfolio
        
        mock_market_data = MagicMock()
        mock_market_data.get_quote = AsyncMock(return_value=None)
        mock_market_data_class.return_value = mock_market_data
        
        # Run analysis
        decisions, events, _ = await analyze_chunks(chunks)
    
    # Verify we got all decisions
    assert len(decisions) >= 8  # 4 models * 2 decisions each = 8 total
    
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
    assert decisions[0].model_provider is not None
    assert decisions[0].model_name is not None
