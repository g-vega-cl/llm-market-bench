"""Reproduction and regression tests verifying DeepSeek Flash usage across subsystems."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import DEEPSEEK_FLASH_MODEL
from core.models import DecisionObject, VerificationResult


@pytest.mark.asyncio
async def test_verification_deepseek_uses_flash():
    """Verify that trade verification for DeepSeek decisions routes to DEEPSEEK_FLASH_MODEL."""
    from core.llm.verification import verify_trading_decision

    decision = DecisionObject(
        signal="BUY",
        confidence=85,
        reasoning="Testing flash verifier",
        ticker="NVDA",
        source_id="src_1",
        price=130.0,
        model_provider="deepseek",
        model_name="deepseek-v4-pro",
    )

    mock_result = VerificationResult(
        status="APPROVED",
        verification_reasoning="Looks good.",
        confidence_score=90,
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=[mock_result])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()

        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        with (
            patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock) as mock_tool_loop,
            patch("core.llm.clients.close_client", new_callable=AsyncMock),
        ):
            await verify_trading_decision(
                decision=decision,
                portfolio_context="Cash: $10,000",
                aggregated_context="Historical context",
            )

            # Check that the tool loop received DEEPSEEK_FLASH_MODEL (arg index 1 or kwargs)
            assert mock_tool_loop.call_args is not None
            passed_model = (
                mock_tool_loop.call_args.args[1]
                if len(mock_tool_loop.call_args.args) > 1
                else mock_tool_loop.call_args.kwargs.get("model_name")
            )
            assert passed_model == DEEPSEEK_FLASH_MODEL

            # Check that instructor completion received DEEPSEEK_FLASH_MODEL
            assert mock_completions.create.call_args is not None
            assert mock_completions.create.call_args.kwargs.get("model") == DEEPSEEK_FLASH_MODEL


@pytest.mark.asyncio
async def test_calendar_ingestion_uses_flash():
    """Verify that CalendarPipeline uses DEEPSEEK_FLASH_MODEL."""
    from core.models import DecisionsResponse
    from ingest.calendar import CalendarPipeline

    with (
        patch("ingest.calendar.get_deepseek_client") as mock_get_client,
        patch("ingest.calendar.get_supabase_client"),
    ):
        mock_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=DecisionsResponse(macro_events=[], reasoning="Test"))
        mock_client.chat.completions = mock_completions
        mock_get_client.return_value = mock_client

        pipeline = CalendarPipeline()
        with (
            patch.object(pipeline, "fetch_html", return_value="<table></table>"),
            patch.object(
                pipeline,
                "parse_events",
                return_value=[
                    {
                        "date": "2026-04-01",
                        "time": "10:00",
                        "country": "USA",
                        "event": "CPI",
                        "forecast": "3.0%",
                        "previous": "3.1%",
                    }
                ],
            ),
            patch("ingest.calendar.add_memory"),
        ):
            await pipeline.run()

        assert mock_completions.create.call_args is not None
        assert mock_completions.create.call_args.kwargs.get("model") == DEEPSEEK_FLASH_MODEL


@pytest.mark.asyncio
async def test_audit_analyzer_uses_flash():
    """Verify that analyze_log_blob uses DEEPSEEK_FLASH_MODEL."""
    from core.audit.analyzer import analyze_log_blob, configure

    configure("test-deepseek-key")

    with patch("core.audit.analyzer.AsyncOpenAI") as mock_openai:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(
            return_value=AsyncMock(choices=[AsyncMock(message=AsyncMock(content=json.dumps([])))])
        )
        mock_openai.return_value = mock_instance

        await analyze_log_blob("Sample test log output")

        assert mock_instance.chat.completions.create.call_args is not None
        assert mock_instance.chat.completions.create.call_args.kwargs.get("model") == DEEPSEEK_FLASH_MODEL


@pytest.mark.asyncio
async def test_memory_consolidation_uses_flash():
    """Verify that consolidate_overlapping_memories uses DEEPSEEK_FLASH_MODEL."""
    from memory.store import consolidate_overlapping_memories

    mock_memories = [
        {
            "id": "mem-1",
            "content": "Fed hints at rate cut in July",
            "embedding": [0.1, 0.2],
            "importance_score": 8,
            "memory_type": "MARKET_EVENT",
        },
        {
            "id": "mem-2",
            "content": "Powell mentions July rate cut possibility",
            "embedding": [0.1, 0.2],
            "importance_score": 8,
            "memory_type": "MARKET_EVENT",
        },
    ]

    mock_resp = MagicMock(
        headline="Consolidated Headline",
        summary="Consolidated Summary",
        importance_score=8,
        memory_type="MARKET_EVENT",
    )

    with (
        patch("memory.store.get_supabase_client") as mock_sb,
        patch("core.llm.get_deepseek_client") as mock_get_ds,
        patch("analysis.consensus.cosine_similarity", return_value=0.95),
        patch("memory.store.add_memory", return_value="new-mem-id"),
    ):
        mock_sb_client = MagicMock()
        mock_sb_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = mock_memories
        mock_sb.return_value = mock_sb_client

        mock_ds_client = MagicMock()
        mock_ds_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_get_ds.return_value = mock_ds_client

        await consolidate_overlapping_memories()

        assert mock_ds_client.chat.completions.create.call_args is not None
        assert mock_ds_client.chat.completions.create.call_args.kwargs.get("model") == DEEPSEEK_FLASH_MODEL


def test_autoresearch_track_models_flash():
    """Verify that AUTORESEARCH_TRACK_MODELS track_default uses DEEPSEEK_FLASH_MODEL."""
    from core import config

    assert config.AUTORESEARCH_TRACK_MODELS.get("track_default") == config.DEEPSEEK_FLASH_MODEL
