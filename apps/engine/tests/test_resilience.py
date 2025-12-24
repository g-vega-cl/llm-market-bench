
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from apps.engine.analyze import analyze_chunks
from apps.engine.core.models import DecisionObject

@pytest.mark.asyncio
async def test_individual_task_failure_does_not_halt_pipeline():
    """Verify that one model failing doesn't stop others."""
    
    async def mock_analyze(provider, model_name, text, source_id):
        if provider == "openai":
            raise Exception("OpenAI is down")
        return DecisionObject(
            signal="BUY",
            confidence=90,
            reasoning="Success",
            ticker="AAPL",
            source_id=source_id
        )

    chunks = [{"source_id": "chunk_1", "content": "test"}]
    
    with patch("apps.engine.core.llm.analyze_with_provider", side_effect=mock_analyze):
        results = await analyze_chunks(chunks)
    
    # 4 models total. OpenAI failed, so we should have 3 results.
    assert len(results) == 3
    for r in results:
        assert r.ticker == "AAPL"

def test_main_ingestion_guardrail(monkeypatch):
    """Test that main.py stops if no newsletters are returned."""
    from apps.engine.main import main
    import sys
    
    # Mock ingest_newsletters to return empty
    monkeypatch.setattr("apps.engine.main.ingest_newsletters", lambda: [])
    # Mock logger to verify it's called
    mock_logger = MagicMock()
    monkeypatch.setattr("apps.engine.main.logger", mock_logger)
    
    # Simulate 'python main.py ingest'
    monkeypatch.setattr(sys, "argv", ["main.py", "ingest"])
    
    main()
    
    # Verify warning was logged
    mock_logger.warning.assert_any_call("No new newsletters found to ingest. Skipping snapshotting and analysis.")
    # Verify database snapshotting wasn't started (get_supabase_client not called)
    # Note: we need to mock it to avoid real connection attempts if it were called
    with patch("apps.engine.main.get_supabase_client") as mock_db:
        main()
        mock_db.assert_not_called()
