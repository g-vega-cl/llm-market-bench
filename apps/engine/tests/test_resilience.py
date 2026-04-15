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
    
    async def mock_analyze(provider, model_name, chunks, context=None, portfolio_context=None, **kwargs):
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
         patch("analyze.MarketDataManager") as mock_market_data_class, \
         patch("memory.embeddings.get_embeddings_batch") as mock_get_embeddings:

        mock_get_embeddings.return_value = [[0.1] * 768]
        
        from unittest.mock import AsyncMock
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
        mock_market_data.is_market_open = AsyncMock(return_value=True)
        mock_market_data_class.return_value = mock_market_data

        decisions, events, _, _ = await analyze_chunks(chunks)

    # 4 models total. OpenAI failed, so we should have 3 results.
    assert len(decisions) == 3
    for r in decisions:
        assert r.ticker == "AAPL"


def test_main_ingestion_guardrail(monkeypatch):
    """Test that main.py stops if no newsletters are returned."""
    from unittest.mock import AsyncMock

    # Mock get_supabase_client BEFORE importing main to prevent DB initialization
    with patch("core.db.get_supabase_client", return_value=MagicMock()), \
         patch("execution.market_data.MarketDataManager") as mock_mdm_cls, \
         patch("execution.portfolio.Portfolio") as mock_portfolio_cls:

        # Setup MarketDataManager mock
        mock_mdm = mock_mdm_cls.return_value
        mock_mdm.is_market_open = AsyncMock(return_value=True)
        mock_mdm.get_quote = AsyncMock(return_value=None)
        mock_mdm.get_quotes = AsyncMock(return_value={})

        # Setup Portfolio mock
        mock_portfolio = MagicMock()
        mock_portfolio_cls.return_value = mock_portfolio
        mock_portfolio.positions = {}
        mock_portfolio.initialize = AsyncMock(return_value=None)
        mock_portfolio.calculate_reg_t_metrics = MagicMock()
        mock_portfolio.save_metrics = AsyncMock(return_value=None)
        mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000 cash")

        # Now it's safe to import main
        from main import main

        # Mock ingest_newsletters to return empty
        monkeypatch.setattr("main.ingest_newsletters", AsyncMock(return_value=[]))
        # Mock logger to verify it's called
        mock_logger = MagicMock()
        monkeypatch.setattr("main.logger", mock_logger)

        # Simulate 'python main.py ingest'
        monkeypatch.setattr(sys, "argv", ["main.py", "ingest"])

        main()

    # Verify warning was logged
    mock_logger.warning.assert_called()


def test_main_dust_cleanup_runs_even_without_newsletters(fully_mocked_main):
    """Test that dust cleanup runs regardless of newsletter data.
    
    Dust cleanup is intentionally designed to run before the newsletter check,
    as it's a safety net for accumulated dust from any source.
    """
    from main import main
    
    md = fully_mocked_main
    md["ingest"].return_value = []  # No newsletters
    md["dust_cleanup"].return_value = None
    
    # Simulate 'python main.py ingest'
    import sys
    sys.argv = ["main.py", "ingest"]
    
    main()
    
    # Verify dust cleanup was called (runs before newsletter check)
    md["dust_cleanup"].assert_called_once()
