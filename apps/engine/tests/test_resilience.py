"""Tests for pipeline resilience and error handling."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from analysis.analyze import analyze_chunks
from core.models import DecisionObject


@pytest.mark.asyncio
async def test_individual_task_failure_does_not_halt_pipeline():
    """Verify that one model failing doesn't stop others."""

    from core.models import DecisionsResponse

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
            )
            for chunk in chunks
        ]
        return DecisionsResponse(decisions=decisions, macro_events=[])

    chunks = [{"source_id": "chunk_1", "content": "test"}]

    with (
        patch("core.llm.analyze_with_provider", side_effect=mock_analyze),
        patch("analysis.analyze.retrieve_top_memories", return_value=""),
        patch("analysis.analyze.Portfolio") as mock_portfolio_class,
        patch("analysis.analyze.MarketDataManager") as mock_market_data_class,
        patch("memory.embeddings.get_embeddings_batch") as mock_get_embeddings,
    ):
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

    from analysis.analyze import MODELS

    # All models except openai should succeed
    expected_count = len(MODELS) - 1
    assert len(decisions) == expected_count
    for r in decisions:
        assert r.ticker == "AAPL"


def test_main_ingestion_guardrail(fully_mocked_main, monkeypatch):
    """Test that main.py stops if no newsletters are returned."""
    from main import main

    md = fully_mocked_main
    # Mock ingest_newsletters to return empty
    md["ingest"].return_value = []

    # Simulate 'python main.py ingest'
    monkeypatch.setattr(sys, "argv", ["main.py", "ingest"])

    main()

    # Verify warning was logged
    md["logger"].warning.assert_called()


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
