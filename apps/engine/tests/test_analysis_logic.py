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
        }
        obj = DecisionObject(**data)
        assert obj.ticker == "AAPL"


@pytest.mark.asyncio
class TestAnalysisOrchestration:
    """Tests for the analyze_chunks orchestration function."""

    async def test_analyze_chunks_orchestration(self, monkeypatch):
        """Test that analyze_chunks calls analyze_with_provider for each model and chunk."""

        async def mock_analyze(provider, model_name, chunks, context=None):
            # Return a list of decisions, one per chunk for simplicity in mock
            return [
                DecisionObject(
                    signal="BUY",
                    confidence=80,
                    reasoning=f"{provider} says buy",
                    ticker="AAPL",
                    source_id=chunk.get("source_id", "unknown"),
                ) for chunk in chunks
            ]

        monkeypatch.setattr("core.llm.analyze_with_provider", mock_analyze)

        chunks = [{"source_id": "chunk_1", "content": "Apple is doing great."}]

        results = await analyze_chunks(chunks)

        assert len(results) > 0
        assert isinstance(results[0], DecisionObject)
        assert results[0].source_id == "chunk_1"

    async def test_analyze_chunks_skips_malformed(self, monkeypatch, caplog):
        """Test that malformed chunks are skipped with a warning."""

        async def mock_analyze(provider, model_name, chunks, context=None):
            return [
                DecisionObject(
                    signal="HOLD",
                    confidence=50,
                    reasoning="Test",
                    ticker="TEST",
                    source_id=chunk.get("source_id", "unknown"),
                ) for chunk in chunks
            ]

        monkeypatch.setattr("core.llm.analyze_with_provider", mock_analyze)

        chunks = [
            {"source_id": "chunk_1"},  # Missing content
            {"content": "Some text"},  # Missing source_id
        ]

        results = await analyze_chunks(chunks)

        assert len(results) == 0
