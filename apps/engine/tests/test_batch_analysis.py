"""Tests for batch analysis logic."""

from unittest.mock import AsyncMock, patch

import pytest

# , DecisionsResponse  <-- Need to import if we mock
from analysis.analyze import analyze_chunks
from core.models import DecisionObject


@pytest.fixture
def mock_llm_analyze():
    """Mock the llm.analyze_with_provider function."""
    with patch("core.llm.analyze_with_provider", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def mock_retrieve_context():
    """Mock the retrieve_top_memories function."""
    with patch("analysis.analyze.retrieve_top_memories") as m:
        m.return_value = "Mocked Context"
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
            signal="BUY",
            confidence=80,
            reasoning="Bullish news 1",
            ticker="AAPL",
            source_id="src_1",
            is_priced_in=False,
            is_priced_in_reasoning="News just broke",
            profit_potential_reasoning="First mover advantage",
            strategy_reasoning="Buy AAPL for long term",
            advance_planning_notes="Plan to hold",
        ),
        DecisionObject(
            signal="SELL",
            confidence=70,
            reasoning="Bearish news 2",
            ticker="GOOGL",
            source_id="src_2",
            is_priced_in=True,
            is_priced_in_reasoning="Already spiked",
            profit_potential_reasoning="Exit before further drop",
            strategy_reasoning="Sell GOOGL now",
            advance_planning_notes="Move to cash",
        ),
    ]
    from core.models import DecisionsResponse

    mock_llm_analyze.return_value = DecisionsResponse(decisions=mock_decisions, macro_events=[])

    chunks = [
        {"source_id": "src_1", "content": "AAPL earnings up"},
        {"source_id": "src_2", "content": "GOOGL earnings down"},
    ]

    # Mock Portfolio and MarketDataManager to avoid Supabase dependency
    with (
        patch("analysis.analyze.Portfolio") as mock_portfolio_class,
        patch("analysis.analyze.MarketDataManager") as mock_market_data_class,
        patch("analysis.pre_filter.summarize_newsletters", AsyncMock(return_value={})),
    ):
        mock_portfolio = MagicMock()
        mock_portfolio.positions = {}
        mock_portfolio.initialize = AsyncMock(return_value=None)
        mock_portfolio.calculate_reg_t_metrics = MagicMock()
        mock_portfolio.save_metrics = AsyncMock(return_value=None)
        mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000 cash")
        mock_portfolio_class.return_value = mock_portfolio

        mock_market_data = MagicMock()
        mock_market_data.get_quote = AsyncMock(return_value=None)
        mock_market_data.get_quotes = AsyncMock(return_value={})
        mock_market_data.get_history = AsyncMock(return_value=[])
        mock_market_data_class.return_value = mock_market_data

        # Run analysis
        decisions, events, _, _ = await analyze_chunks(chunks)

    from analysis.analyze import MODELS

    model_count = len(MODELS)
    # Verify we got all decisions (model_count * 2 decisions per model)
    assert len(decisions) >= model_count * 2

    # Verify analyze_with_provider was called twice per model (macro + trading pass)
    assert mock_llm_analyze.call_count == model_count * 2


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


@pytest.mark.asyncio
async def test_orchestrator_logs_gather_exceptions_with_exc_info():
    """Verify that the orchestrator logs returned gather exceptions with exc_info=res so traceback is not NoneType: None."""
    from unittest.mock import patch

    with (
        patch("analysis.analyze.retrieve_top_memories", return_value=[]),
        patch("analysis.analyze.get_top_trending_concepts", return_value=[]),
        patch("analysis.analyze.Portfolio.initialize", new=AsyncMock()),
        patch("analysis.analyze.Portfolio.calculate_reg_t_metrics"),
        patch("analysis.analyze.Portfolio.save_metrics", new=AsyncMock()),
        patch("analysis.analyze.Portfolio.get_portfolio_summary", new=AsyncMock(return_value="")),
        patch("core.macro_tracker.get_global_macro_context", new=AsyncMock(return_value="")),
        patch("core.llm.analyze_with_provider", side_effect=ValueError("Test gather exception")),
        patch("analysis.pre_filter.summarize_newsletters", AsyncMock(return_value={})),
        patch("analysis.analyze.logger") as mock_logger,
    ):
        await analyze_chunks([{"source_id": "s1", "content": "Test news", "sender": "s", "subject": "subj"}])

        assert mock_logger.error.called
        calls = mock_logger.error.call_args_list
        found = False
        for call in calls:
            if "Batch analysis task failed" in call.args[0]:
                kwargs = call.kwargs
                assert "exc_info" in kwargs
                assert isinstance(kwargs["exc_info"], ValueError)
                found = True
        assert found
        for call in mock_logger.exception.call_args_list:
            assert "Batch analysis task failed" not in call.args[0]
