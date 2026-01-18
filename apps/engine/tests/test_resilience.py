"""Tests for pipeline resilience and error handling."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from analyze import analyze_chunks
from core.models import DecisionObject


@pytest.mark.asyncio
async def test_individual_task_failure_does_not_halt_pipeline():
    """Verify that one model failing doesn't stop others."""

    from core.models import DecisionsResponse
    from unittest.mock import MagicMock, patch
    
    async def mock_analyze(provider, model_name, chunks, context=None, portfolio_context=None):
        if provider == "openai":
            raise Exception("OpenAI is down")
        
        decisions = [
            DecisionObject(
                signal="BUY",
                confidence=90,
                reasoning="Success",
                ticker="AAPL",
                source_id=chunk.get("source_id", "unknown"),
            ) for chunk in chunks
        ]
        return DecisionsResponse(decisions=decisions, macro_events=[])

    chunks = [{"source_id": "chunk_1", "content": "test"}]

    with patch("core.llm.analyze_with_provider", side_effect=mock_analyze), \
         patch("analyze.retrieve_context_batch", return_value=[""]), \
         patch("analyze.Portfolio") as mock_portfolio_class, \
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
        
        decisions, events = await analyze_chunks(chunks)

    # 4 models total. OpenAI failed, so we should have 3 results.
    assert len(decisions) == 3
    for r in decisions:
        assert r.ticker == "AAPL"


def test_main_ingestion_guardrail(monkeypatch):
    """Test that main.py stops if no newsletters are returned."""
    from main import main

    # Mock ingest_newsletters to return empty
    monkeypatch.setattr("main.ingest_newsletters", lambda: [])
    # Mock logger to verify it's called
    mock_logger = MagicMock()
    monkeypatch.setattr("main.logger", mock_logger)

    # Simulate 'python main.py ingest'
    monkeypatch.setattr(sys, "argv", ["main.py", "ingest"])

    main()

    # Verify warning was logged
    mock_logger.warning.assert_called()


def test_main_does_not_call_db_when_no_newsletters(monkeypatch):
    """Test that database operations are skipped when no newsletters found."""
    from main import main

    # Mock ingest_newsletters to return empty
    monkeypatch.setattr("main.ingest_newsletters", lambda: [])
    # Mock logger
    mock_logger = MagicMock()
    monkeypatch.setattr("main.logger", mock_logger)

    # Simulate 'python main.py ingest'
    monkeypatch.setattr(sys, "argv", ["main.py", "ingest"])

    with patch("main.get_supabase_client") as mock_db:
        main()
        mock_db.assert_not_called()
