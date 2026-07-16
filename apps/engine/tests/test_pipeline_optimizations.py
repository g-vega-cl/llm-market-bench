import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analysis.consensus import _synthesize_and_promote_group
from core.llm.tools import execute_stock_screener_tool
from core.models import MacroEvent
from execution.market_data import MarketDataManager
from ingest.newsletter import NewsletterSnapshot, ingest_newsletters
from main import _stage_decision_processing

# --- 1. Batched Cache Query Test ---


@pytest.mark.asyncio
async def test_get_quotes_uses_batched_cache_query():
    with patch("execution.market_data.get_supabase_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        # Mock the chained database query
        mock_table = mock_client.table.return_value
        mock_select = mock_table.select.return_value
        mock_in = mock_select.in_.return_value
        mock_execute = mock_in.execute.return_value
        import datetime

        now_str = datetime.datetime.now(datetime.UTC).isoformat()

        mock_execute.data = [
            {
                "ticker": "AAPL",
                "price": 175.0,
                "market_cap": 3000000000000.0,
                "fetched_at": now_str,
            },
            {
                "ticker": "MSFT",
                "price": 400.0,
                "market_cap": 3000000000000.0,
                "fetched_at": now_str,
            },
        ]

        manager = MarketDataManager()
        # Force cache TTL checks to pass by using a fresh fetched_at or setting TTL high
        manager.cache_ttl_seconds = 3600

        results = await manager.get_quotes(["AAPL", "MSFT"])

        # Verify that select().in_().execute() was called once
        mock_client.table.assert_called_with("market_data_cache")
        mock_select.in_.assert_called_once_with("ticker", ["AAPL", "MSFT"])
        assert "AAPL" in results


# --- 2. Parallel Gmail Fetch Test ---


@pytest.mark.asyncio
async def test_ingest_newsletters_parallel_fetch():
    mock_service = MagicMock()
    mock_list = mock_service.users().messages().list.return_value
    mock_list.execute.return_value = {"messages": [{"id": "msg1"}, {"id": "msg2"}, {"id": "msg3"}]}

    async def slow_fetch(service, msg_ref):
        await asyncio.sleep(0.1)
        return NewsletterSnapshot(
            source_id=f"id_{msg_ref['id']}",
            chunk_hash=f"hash_{msg_ref['id']}",
            sender="sender@test.com",
            date="2026-07-14T12:00:00+00:00",
            subject="Test subject",
            content="News content",
            ingested_at="2026-07-14T12:00:00+00:00",
        ), "sender@test.com"

    with (
        patch("ingest.newsletter.get_gmail_service", return_value=mock_service),
        patch("ingest.newsletter._fetch_raw_message", side_effect=slow_fetch),
        patch("ingest.newsletter.clean_newsletter_content", new_callable=AsyncMock) as mock_clean,
    ):
        mock_clean.return_value = "Clean content"

        start_time = time.time()
        await ingest_newsletters(newer_than_days=1)
        elapsed = time.time() - start_time

        # If run sequentially, 3 messages with 0.1s sleep would take >= 0.3s.
        # If parallel, it should take < 0.2s.
        assert elapsed < 0.25, f"Execution took too long: {elapsed:.2f}s (should be parallel)"


# --- 3. Parallel Stock Screener Enrichment Test ---


@pytest.mark.asyncio
async def test_screener_parallel_enrichment():
    mock_results = [
        {"symbol": "AAPL", "companyName": "Apple", "price": 175.0, "marketCap": 3e12},
        {"symbol": "MSFT", "companyName": "Microsoft", "price": 400.0, "marketCap": 3e12},
        {"symbol": "GOOGL", "companyName": "Google", "price": 150.0, "marketCap": 2e12},
    ]

    async def slow_get_history(ticker, days=14, force_refresh=False):
        await asyncio.sleep(0.1)
        return [{"price": 100.0, "fetched_at": "2026-07-14"}]

    with (
        patch(
            "execution.market_data.MarketDataManager.screen_stocks", new_callable=AsyncMock, return_value=mock_results
        ),
        patch("execution.market_data.MarketDataManager.get_history", side_effect=slow_get_history),
    ):
        start_time = time.time()
        # Call screener tool
        await execute_stock_screener_tool(sector="Technology", limit=3)
        elapsed = time.time() - start_time

        # Sequential: >= 0.3s, Parallel: < 0.2s
        assert elapsed < 0.25, f"Enrichment took too long: {elapsed:.2f}s (should be parallel)"


# --- 4. Parallel Scenario Asset Discovery Test ---


@pytest.mark.asyncio
async def test_scenario_parallel_discovery():
    sample_occurrences = [
        MacroEvent(
            event_name="Test Event",
            impact="BULLISH",
            reasoning="Test Reasoning",
            source_id="src1",
            is_ongoing=False,
            is_future_catalyst=False,
            importance_score=5,
            confidence=80,
        )
    ]

    # Mock synthesize_event to return 2 scenarios
    mock_synthesis = {
        "name": "Synthesized Event",
        "summary": "Synthesized Summary",
        "scenarios": [
            {"cleanHeader": "Scenario A", "outcome": "Outcome A", "tradingPlan": "Plan A", "percentage": "50%"},
            {"cleanHeader": "Scenario B", "outcome": "Outcome B", "tradingPlan": "Plan B", "percentage": "50%"},
        ],
    }

    async def slow_discover(theme, context=None):
        await asyncio.sleep(0.1)
        return [{"ticker": "AAPL", "name": "Apple", "reason": "Test"}]

    mock_discovery = MagicMock()
    mock_discovery.discover_assets = AsyncMock(side_effect=slow_discover)

    with (
        patch("analysis.consensus.synthesize_event", new_callable=AsyncMock, return_value=mock_synthesis),
        patch("analysis.consensus.find_potential_ancestors", return_value=[]),
        patch("analysis.consensus.analyze_event_relationship", new_callable=AsyncMock, return_value={}),
        patch("analysis.consensus.add_memory", return_value="mem1"),
    ):
        start_time = time.time()
        await _synthesize_and_promote_group(sample_occurrences, mock_discovery, sim_threshold=0.75)
        elapsed = time.time() - start_time

        # Sequential: >= 0.2s, Parallel: < 0.15s
        assert elapsed < 0.18, f"Scenario discovery took too long: {elapsed:.2f}s (should be parallel)"


# --- 5. Consensus Double-Invocation Bypass Test ---


@pytest.mark.asyncio
async def test_consensus_double_invocation_bypass():
    with (
        patch("main.process_consensus", new_callable=AsyncMock) as mock_consensus,
        patch("main.run_contrarian_analysis", new_callable=AsyncMock, return_value=([], [])),
        patch("main.analyze_momentum", new_callable=AsyncMock),
        patch("main.decay_stale_concepts", new_callable=AsyncMock),
        patch("memory.store.decay_memories"),
    ):
        # Case A: consensus_events is passed (pre-computed). Background task should skip process_consensus.
        await _stage_decision_processing(
            decisions=[],
            macro_events=[],
            data=[],
            aggregated_context="",
            uncrowded_context="",
            sb_client=MagicMock(),
            consensus_events=[],  # Pre-computed
        )
        mock_consensus.assert_not_called()

        # Case B: consensus_events is None. Background task should call process_consensus.
        await _stage_decision_processing(
            decisions=[],
            macro_events=[],
            data=[],
            aggregated_context="",
            uncrowded_context="",
            sb_client=MagicMock(),
            consensus_events=None,  # Not pre-computed
        )
        mock_consensus.assert_called_once()
