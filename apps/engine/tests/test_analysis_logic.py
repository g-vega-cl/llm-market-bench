"""Tests for analysis logic and Pydantic models."""

import pytest
from pydantic import ValidationError

from analyze import analyze_chunks
from core.models import DecisionObject


class TestDecisionObject:
    """Tests for the DecisionObject Pydantic model."""

    def test_valid_decision_object(self):
        """Test that a valid dictionary can be parsed into a DecisionObject."""
        data = {
            "signal": "BUY",
            "confidence": 85,
            "reasoning": "Strong earnings report.",
            "ticker": "AAPL",
            "source_id": "news_123",
            "is_priced_in": False,
            "is_priced_in_reasoning": "News just broke",
            "profit_potential_reasoning": "First mover advantage",
            "strategy_reasoning": "Bullish on Apple due to new AI chips.",
            "advance_planning_notes": "None"
        }
        obj = DecisionObject(**data)
        assert obj.signal == "BUY"
        assert obj.confidence == 85
        assert obj.ticker == "AAPL"

    def test_invalid_signal(self):
        """Test that invalid signals raise a ValidationError."""
        data = {
            "signal": "PANIC_SELL",  # Invalid literal
            "confidence": 85,
            "reasoning": "Something bad.",
            "ticker": "AAPL",
            "source_id": "news_123",
            "is_priced_in": False,
            "is_priced_in_reasoning": "Logic",
            "profit_potential_reasoning": "Profit"
        }
        with pytest.raises(ValidationError):
            DecisionObject(**data)

    def test_confidence_range(self):
        """Test that confidence must be between 0 and 100."""
        data = {
            "signal": "HOLD",
            "confidence": 105,  # Out of range
            "reasoning": "Too confident.",
            "ticker": "AAPL",
            "source_id": "news_123",
            "is_priced_in": False,
            "is_priced_in_reasoning": "Logic",
            "profit_potential_reasoning": "Profit"
        }
        with pytest.raises(ValidationError):
            DecisionObject(**data)

    def test_ticker_uppercase(self):
        """Test that ticker symbols are automatically uppercased."""
        data = {
            "signal": "BUY",
            "confidence": 50,
            "reasoning": "Test.",
            "ticker": "aapl",
            "source_id": "news_123",
            "is_priced_in": False,
            "is_priced_in_reasoning": "Logic",
            "profit_potential_reasoning": "Profit"
        }
        obj = DecisionObject(**data)
        assert obj.ticker == "AAPL"


@pytest.mark.asyncio
class TestAnalysisOrchestration:
    """Tests for the analyze_chunks orchestration function."""

    async def test_analyze_chunks_orchestration(self, monkeypatch):
        """Test that analyze_chunks calls analyze_with_provider for each model and chunk."""

        from core.models import DecisionsResponse
        from unittest.mock import MagicMock, patch
        
        async def mock_analyze(provider, model_name, chunks, context=None, portfolio_context=None):
            # Return a DecisionsResponse object
            decisions = [
                DecisionObject(
                    signal="BUY",
                    confidence=80,
                    reasoning=f"{provider} says buy",
                    ticker="AAPL",
                    source_id=chunk.get("source_id", "unknown"),
                    is_priced_in=False,
                    is_priced_in_reasoning="Logic",
                    profit_potential_reasoning="Profit",
                    strategy_reasoning="Mock strategy",
                    advance_planning_notes="Mock notes"
                ) for chunk in chunks
            ]
            return DecisionsResponse(decisions=decisions, macro_events=[])

        monkeypatch.setattr("core.llm.analyze_with_provider", mock_analyze)

        chunks = [{"source_id": "chunk_1", "content": "Apple is doing great."}]

        # Mock Portfolio and MarketDataManager to avoid Supabase dependency
        with patch("analyze.Portfolio") as mock_portfolio_class, \
             patch("analyze.MarketDataManager") as mock_market_data_class, \
             patch("memory.embeddings.get_embeddings_batch") as mock_get_embeddings:

            mock_get_embeddings.return_value = [[0.1] * 768]
            
            # Mock portfolio instance
            from unittest.mock import AsyncMock
            mock_portfolio = MagicMock()
            mock_portfolio.positions = {}
            mock_portfolio.initialize = AsyncMock(return_value=None)
            mock_portfolio.calculate_reg_t_metrics = MagicMock()
            mock_portfolio.save_metrics = AsyncMock(return_value=None)
            mock_portfolio.get_portfolio_summary = MagicMock(return_value="Portfolio: $10,000 cash")
            mock_portfolio_class.return_value = mock_portfolio
            
            # Mock market data manager
            mock_market_data = MagicMock()
            mock_market_data.get_quote = AsyncMock(return_value=None)
            mock_market_data_class.return_value = mock_market_data

            decisions, events, _ = await analyze_chunks(chunks)

        assert len(decisions) > 0
        assert isinstance(decisions[0], DecisionObject)
        assert decisions[0].source_id == "chunk_1"

    async def test_analyze_chunks_skips_malformed(self, monkeypatch, caplog):
        """Test that malformed chunks are skipped with a warning."""

        from core.models import DecisionsResponse
        from unittest.mock import MagicMock, patch
        
        async def mock_analyze(provider, model_name, chunks, context=None, portfolio_context=None):
            decisions = [
                DecisionObject(
                    signal="HOLD",
                    confidence=50,
                    reasoning="Test",
                    ticker="TEST",
                    source_id=chunk.get("source_id", "unknown"),
                    is_priced_in=False,
                    is_priced_in_reasoning="Logic",
                    profit_potential_reasoning="Profit",
                    strategy_reasoning="Mock strategy",
                    advance_planning_notes="Mock notes"
                ) for chunk in chunks
            ]
            return DecisionsResponse(decisions=decisions, macro_events=[])

        monkeypatch.setattr("core.llm.analyze_with_provider", mock_analyze)

        chunks = [
            {"source_id": "chunk_1"},  # Missing content
            {"content": "Some text"},  # Missing source_id
        ]

        # Mock Portfolio and MarketDataManager to avoid Supabase dependency
        with patch("analyze.Portfolio") as mock_portfolio_class, \
             patch("analyze.MarketDataManager") as mock_market_data_class, \
             patch("memory.embeddings.get_embeddings_batch") as mock_get_embeddings:

            mock_get_embeddings.return_value = [[0.1] * 768]
            
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

            decisions, events, _ = await analyze_chunks(chunks)

        assert len(decisions) == 0
        assert len(events) == 0
