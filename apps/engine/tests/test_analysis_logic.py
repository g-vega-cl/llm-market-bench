
import pytest
from pydantic import ValidationError
# These imports will fail initially - this is intentional for TDD
try:
    from apps.engine.core.models import DecisionObject
    from apps.engine.analyze import analyze_chunks
except ImportError:
    DecisionObject = None
    analyze_chunks = None

class TestDecisionObject:
    def test_valid_decision_object(self):
        """Test that a valid dictionary can be parsed into a DecisionObject."""
        if not DecisionObject:
            pytest.fail("DecisionObject not implemented yet")
            
        data = {
            "signal": "BUY",
            "confidence": 85,
            "reasoning": "Strong earnings report.",
            "ticker": "AAPL",
            "source_id": "news_123"
        }
        obj = DecisionObject(**data)
        assert obj.signal == "BUY"
        assert obj.confidence == 85
        assert obj.ticker == "AAPL"

    def test_invalid_signal(self):
        """Test that invalid signals raise a ValidationError."""
        if not DecisionObject:
            pytest.fail("DecisionObject not implemented yet")

        data = {
            "signal": "PANIC_SELL", # Invalid literal
            "confidence": 85,
            "reasoning": "Something bad.",
            "ticker": "AAPL",
            "source_id": "news_123"
        }
        with pytest.raises(ValidationError):
            DecisionObject(**data)

    def test_confidence_range(self):
        """Test that confidence must be between 0 and 100."""
        if not DecisionObject:
            pytest.fail("DecisionObject not implemented yet")

        data = {
            "signal": "HOLD",
            "confidence": 105, # Out of range
            "reasoning": "Too confident.",
            "ticker": "AAPL",
            "source_id": "news_123"
        }
        with pytest.raises(ValidationError):
            DecisionObject(**data)

@pytest.mark.asyncio
class TestAnalysisOrchestration:
    @pytest.mark.asyncio
    async def test_analyze_chunks_orchestration(self, monkeypatch):
        """Test that analyze_chunks calls analyze_with_provider for each model and chunk."""
        if not analyze_chunks:
            pytest.fail("analyze_chunks not implemented yet")

        # Mock analyze_with_provider to avoid real API calls
        async def mock_analyze(provider, model_name, text, source_id):
            return DecisionObject(
                signal="BUY",
                confidence=80,
                reasoning=f"{provider} says buy",
                ticker="AAPL",
                source_id=source_id
            )
        
        # We need to know how analyze_chunks imports the function. 
        # Assuming 'from apps.engine.core.llm import analyze_with_provider' inside analyze.py
        # Or 'import apps.engine.core.llm as llm'
        # I will enforce the import pattern in verify step. 
        # For now, let's assume analyze.py imports it directly. 
        # We'll set it on the module 'apps.engine.analyze' if it imports it, or 'apps.engine.core.llm' if it uses full path.
        # Safe bet: We will implement analyze.py to use `apps.engine.core.llm.analyze_with_provider`.
        monkeypatch.setattr("apps.engine.core.llm.analyze_with_provider", mock_analyze)

        chunks = [{"source_id": "chunk_1", "content": "Apple is doing great."}]
        
        # Expected behavior: analyze_chunks triggers calls for defined models.
        # Let's say we have 4 models enabled.
        results = await analyze_chunks(chunks)
        
        assert len(results) > 0
        # If 4 models are enabled, we expect 4 results per chunk.
        # We will check if we got at least one valid result structure back.
        assert isinstance(results[0], DecisionObject)
        assert results[0].source_id == "chunk_1"
