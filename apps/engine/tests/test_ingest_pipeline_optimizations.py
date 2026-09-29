"""Hermetic tests for ingest pipeline optimizations, tool auditing, and resilience."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.handlers import base
from core.models import MacroEvent
from execution.providers.fmp import FMPProvider


@pytest.mark.asyncio
async def test_execute_tool_audits_duration_for_all_tools():
    """Verify execute_tool measures execution duration and calls async_record_tool_audit for any tool."""
    with (
        patch("core.llm.handlers.base.async_record_tool_audit") as mock_audit,
        patch("core.llm.tools.execute_stock_tool", new_callable=AsyncMock) as mock_stock,
    ):
        mock_stock.return_value = "AAPL: $200.00"

        res = await base.execute_tool("get_stock_quote", {"ticker": "AAPL"}, "test-model")

        assert res == "AAPL: $200.00"
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs if mock_audit.call_args.kwargs else mock_audit.call_args[1]
        assert call_kwargs.get("tool_name") == "get_stock_quote"
        assert "duration_ms" in call_kwargs
        assert isinstance(call_kwargs["duration_ms"], int)
        assert call_kwargs.get("model_name") == "test-model"


@pytest.mark.asyncio
async def test_execute_tool_defensive_ticker_and_symbol_fallback():
    """Verify execute_tool handles 'symbol' key alias and missing ticker without raising KeyError."""
    with patch("core.llm.tools.execute_stock_tool", new_callable=AsyncMock) as mock_stock:
        mock_stock.return_value = "MSFT: $420.00"

        # 1. Model provided {"symbol": "MSFT"} instead of {"ticker": "MSFT"}
        res = await base.execute_tool("get_stock_quote", {"symbol": "MSFT"}, "test-model")
        assert res == "MSFT: $420.00"

    # 2. Model provided empty dict without ticker or symbol
    res_empty = await base.execute_tool("get_stock_quote", {}, "test-model")
    assert "Error: Missing required 'ticker' argument" in res_empty


@pytest.mark.asyncio
async def test_execute_tool_catches_unhandled_tool_exception():
    """Verify execute_tool catches unexpected tool exceptions, records status='error', and returns clean error string."""
    with (
        patch("core.llm.handlers.base.async_record_tool_audit") as mock_audit,
        patch("core.llm.tools.execute_stock_tool", new_callable=AsyncMock) as mock_stock,
    ):
        mock_stock.side_effect = RuntimeError("Provider socket timeout")

        res = await base.execute_tool("get_stock_quote", {"ticker": "AAPL"}, "test-model")
        assert "Error executing get_stock_quote" in res
        assert "Provider socket timeout" in res

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs if mock_audit.call_args.kwargs else mock_audit.call_args[1]
        assert call_kwargs.get("status") == "error"


@pytest.mark.asyncio
async def test_process_consensus_parallelizes_group_synthesis():
    """Verify process_consensus processes multiple qualifying groups concurrently."""
    from analysis.consensus import process_consensus

    events = [
        MacroEvent(
            event_name="Event Alpha",
            reasoning="Reasoning A",
            impact="BULLISH",
            source_id="src1",
            model_provider="openai",
            model_name="openai/gpt-5.6-luna",
            confidence=85,
        ),
        MacroEvent(
            event_name="Event Alpha",
            reasoning="Reasoning A2",
            impact="BULLISH",
            source_id="src1",
            model_provider="anthropic",
            model_name="anthropic/claude-haiku-4-5",
            confidence=85,
        ),
        MacroEvent(
            event_name="Event Beta",
            reasoning="Reasoning B",
            impact="BEARISH",
            source_id="src2",
            model_provider="openai",
            model_name="openai/gpt-5.6-luna",
            confidence=85,
        ),
        MacroEvent(
            event_name="Event Beta",
            reasoning="Reasoning B2",
            impact="BEARISH",
            source_id="src2",
            model_provider="anthropic",
            model_name="anthropic/claude-haiku-4-5",
            confidence=85,
        ),
    ]

    active_tasks = 0
    max_concurrent_seen = 0

    async def mock_synthesize(group, discovery_service, sim_threshold):
        nonlocal active_tasks, max_concurrent_seen
        active_tasks += 1
        max_concurrent_seen = max(max_concurrent_seen, active_tasks)
        await asyncio.sleep(0.05)
        active_tasks -= 1
        return {"event_name": group[0].event_name, "promoted": True}

    with (
        patch("analysis.consensus._get_event_embeddings", new_callable=AsyncMock) as mock_emb,
        patch("analysis.consensus._synthesize_and_promote_group", side_effect=mock_synthesize),
    ):
        mock_emb.return_value = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]]

        promoted = await process_consensus(events, threshold=2.0)
        assert len(promoted) == 2
        # Max concurrency should be > 1 since they run in parallel
        assert max_concurrent_seen >= 2


@pytest.mark.asyncio
async def test_fmp_provider_caches_quarterly_tier_restriction():
    """Verify FMPProvider remembers 402 on quarterly metrics and bypasses quarterly calls on subsequent tickers."""
    provider = FMPProvider()
    provider.api_key = "mock_key"
    FMPProvider._quarterly_metrics_supported = None  # Reset state

    quarter_resp = MagicMock(status_code=402)
    annual_resp = MagicMock(status_code=200)
    annual_resp.json.return_value = [{"symbol": "XLV", "peRatio": 18.5, "date": "2026-01-01"}]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        # First ticker (XLV): quarterly fails with 402, retries annual
        mock_get.side_effect = [
            quarter_resp,  # key-metrics quarter
            quarter_resp,  # ratios quarter
            annual_resp,  # key-metrics annual
            annual_resp,  # ratios annual
            annual_resp,  # key-metrics annual for 2nd ticker
            annual_resp,  # ratios annual for 2nd ticker
        ]

        metrics1 = await provider.get_key_metrics("XLV", period="quarter", limit=1)
        assert len(metrics1) == 1
        assert FMPProvider._quarterly_metrics_supported is False
        assert mock_get.call_count == 4

        # Second ticker (UUP): should directly request annual, bypassing the 2 failed quarterly requests
        metrics2 = await provider.get_key_metrics("UUP", period="quarter", limit=1)
        assert len(metrics2) == 1
        # Call count should increase by only 2 (for annual), not 4
        assert mock_get.call_count == 6


@pytest.mark.asyncio
async def test_run_ingest_dry_run_bypasses_market_and_executes_no_trades():
    """Verify run_ingest(dry_run=True) bypasses market hours and executes 0 live orders or DB writes."""
    import main
    from core.models import DecisionObject
    from execution.validation import ValidationStatus

    sample_decision = DecisionObject(
        ticker="AAPL",
        signal="BUY",
        allocation_percentage=10,
        model_name="openai/gpt-5.6-luna",
        model_provider="openai",
        reasoning="Test dry run reasoning",
        confidence=85,
        source_id="test_src_1",
    )

    with (
        patch("core.utils.is_market_open_with_logging", new_callable=AsyncMock, return_value=False) as mock_market,
        patch("main.get_supabase_client") as mock_sb,
        patch(
            "main.ingest_newsletters",
            new_callable=AsyncMock,
            return_value=[{"source_id": "test", "content": "text"}],
        ),
        patch("main.analyze_chunks", new_callable=AsyncMock) as mock_analyze,
        patch("main.validate_decision", new_callable=AsyncMock) as mock_validate,
        patch("main.validate_semantic_overlap", new_callable=AsyncMock, return_value=None),
        patch("main.verify_trading_decision", new_callable=AsyncMock) as mock_verify,
        patch("main.save_decision") as mock_save,
        patch("main.Portfolio") as MockPortfolio,
        patch(
            "main.analyze_market_feeling",
            new_callable=AsyncMock,
            return_value={"sentiment_label": "BULLISH", "sentiment_emoji": "🚀"},
        ),
        patch("execution.market_data.MarketDataManager") as MockMDM,
    ):
        mock_analyze.return_value = ([sample_decision], [], "", "")
        mock_validate.return_value = MagicMock(status=ValidationStatus.PASSED, market_price=200.0)

        portfolio_instance = MagicMock()
        portfolio_instance.initialize = AsyncMock()
        portfolio_instance.positions = {}
        portfolio_instance.metrics = MagicMock(buying_power=100000.0, total_equity=100000.0)
        portfolio_instance.validate_trade.return_value = MagicMock(passed=True)
        portfolio_instance.execute_trade = AsyncMock()
        MockPortfolio.return_value = portfolio_instance

        mock_mdm_instance = MagicMock()
        mock_mdm_instance.get_quotes = AsyncMock(return_value={"AAPL": MagicMock(price=200.0)})
        mock_mdm_instance.get_quote = AsyncMock(return_value=MagicMock(exists=True, price=200.0))
        MockMDM.return_value = mock_mdm_instance

        mock_verify.return_value = MagicMock(
            status="APPROVED", verification_reasoning="Passed", confidence_score=95, alternative_ticker=None
        )

        mock_sb_client = MagicMock()
        mock_sb_client.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
        mock_sb.return_value = mock_sb_client

        await main.run_ingest(dry_run=True)

        # 1. Market open check was bypassed (not called because dry_run=True)
        assert not mock_market.called
        # 2. execute_trade was NEVER called because dry_run=True
        assert not portfolio_instance.execute_trade.called
        # 3. Supabase save_decision was NEVER called
        assert not mock_save.called
