"""Tests verifying that reasoning_effort='none' is consistently passed for OpenAI tool calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from autoresearch import prompt_store, researcher
from core.llm import analysis, clients, events, handlers, verification
from core.models import DecisionObject, VerificationResult


class DummyResponse(BaseModel):
    decisions: list = []
    macro_events: list = []


@pytest.mark.asyncio
async def test_openai_analysis_injects_reasoning_effort_none():
    """Verify analyze_with_provider passes reasoning_effort='none' for OpenAI."""
    mock_client = MagicMock()
    recorded_kwargs = []

    async def mock_create(**kwargs):
        recorded_kwargs.append(kwargs)
        return DummyResponse()

    mock_client.chat.completions.create = mock_create

    with (
        patch.dict(clients.CLIENT_FACTORIES, {"openai": lambda: mock_client}),
        patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock),
        patch("autoresearch.prompt_store.get_active_prompt", new_callable=AsyncMock, return_value=None),
        patch("core.llm.analysis.log_reasoning_trace", new_callable=AsyncMock),
    ):
        await analysis.analyze_with_provider(
            provider="openai",
            model_name="gpt-5.6-luna",
            chunks=[{"source_id": "src-1", "content": "Sample content"}],
            response_model=DummyResponse,
        )

    assert len(recorded_kwargs) > 0, "Expected chat.completions.create call during extraction"
    assert recorded_kwargs[0].get("reasoning_effort") == "none", (
        f"Expected reasoning_effort='none' in kwargs, got {recorded_kwargs[0]}"
    )


@pytest.mark.asyncio
async def test_openai_events_relationship_injects_reasoning_effort_none():
    """Verify analyze_event_relationship passes reasoning_effort='none' for OpenAI."""
    mock_client = MagicMock()
    recorded_kwargs = []

    async def mock_create(**kwargs):
        recorded_kwargs.append(kwargs)
        mock_resp = MagicMock()
        mock_resp.parent_index = None
        mock_resp.relationship_type = None
        mock_resp.should_resolve = False
        return mock_resp

    mock_client.chat.completions.create = mock_create

    with (
        patch("core.llm.events.clients.get_openai_client", return_value=mock_client),
        patch("core.llm.events.log_reasoning_trace", new_callable=AsyncMock),
    ):
        await events.analyze_event_relationship(
            new_event="CPI released",
            potential_ancestors=[{"id": "1", "content": "Prior CPI"}],
        )

    assert len(recorded_kwargs) > 0, "Expected chat.completions.create call during event relationship analysis"
    assert recorded_kwargs[0].get("reasoning_effort") == "none", (
        f"Expected reasoning_effort='none' in kwargs, got {recorded_kwargs[0]}"
    )


@pytest.mark.asyncio
async def test_openai_handler_tool_loop_injects_reasoning_effort_none():
    """Verify handlers.openai.run_tool_loop passes reasoning_effort='none'."""
    raw_client = MagicMock()
    recorded_kwargs = []

    async def mock_create(**kwargs):
        recorded_kwargs.append(kwargs)
        mock_msg = MagicMock()
        mock_msg.tool_calls = None
        mock_msg.model_dump.return_value = {"role": "assistant", "content": "done"}
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=mock_msg)]
        return mock_resp

    raw_client.chat.completions.create = mock_create

    messages = [{"role": "user", "content": "analyze market"}]
    await handlers.openai.run_tool_loop(
        raw_client=raw_client,
        model_name="gpt-5.6-luna",
        messages=messages,
        provider="openai",
    )

    assert len(recorded_kwargs) > 0, "Expected chat.completions.create call during tool loop"
    assert recorded_kwargs[0].get("reasoning_effort") == "none", (
        f"Expected reasoning_effort='none' in kwargs, got {recorded_kwargs[0]}"
    )


@pytest.mark.asyncio
async def test_openai_verification_injects_reasoning_effort_none():
    """Verify verify_trading_decision passes reasoning_effort='none' for OpenAI."""
    mock_client = MagicMock()
    recorded_kwargs = []

    async def mock_create(**kwargs):
        recorded_kwargs.append(kwargs)
        return VerificationResult(
            status="APPROVED",
            verification_reasoning="Looks good",
            confidence_score=90,
        )

    mock_client.chat.completions.create = mock_create

    decision = DecisionObject(
        ticker="AAPL",
        signal="BUY",
        model_provider="openai",
        model_name="gpt-5.6-luna",
        quantity=10,
        confidence=85,
        reasoning="Strong trend",
        source_id="src-1",
    )

    mock_quote = MagicMock(price=150.0, exists=True)

    with (
        patch.dict(clients.CLIENT_FACTORIES, {"openai": lambda: mock_client}),
        patch("core.llm.verification.retrieve_for_decision", return_value=""),
        patch("execution.market_data.MarketDataManager.get_quote", new_callable=AsyncMock, return_value=mock_quote),
        patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock),
        patch("core.llm.verification.log_reasoning_trace", new_callable=AsyncMock),
    ):
        result = await verification.verify_trading_decision(
            decision=decision,
            portfolio_context="No positions",
            aggregated_context="Bullish market",
        )

    assert result.status == "APPROVED"
    assert len(recorded_kwargs) > 0, "Expected chat.completions.create call during verification extraction"
    assert recorded_kwargs[0].get("reasoning_effort") == "none", (
        f"Expected reasoning_effort='none' in kwargs, got {recorded_kwargs[0]}"
    )


@pytest.mark.asyncio
async def test_openai_autoresearch_injects_reasoning_effort_none():
    """Verify run_research passes reasoning_effort='none' for OpenAI."""
    mock_client = MagicMock()
    recorded_kwargs = []

    async def mock_create(**kwargs):
        recorded_kwargs.append(kwargs)
        return researcher.PromptResearchResult(
            new_prompt_text="Updated strategy",
            selected_tools=["get_stock_quote"],
            change_description="Testing strategy update",
            experiment_type="incremental",
            research_reasoning="Refined prompt",
            confidence=80,
        )

    mock_client.chat.completions.create = mock_create

    with (
        patch(
            "autoresearch.researcher._get_client_and_provider_for_model",
            return_value=(mock_client, "openai"),
        ),
        patch("autoresearch.researcher._load_research_program", return_value="program content"),
        patch("autoresearch.tools.query_trade_postmortems", new_callable=AsyncMock, return_value=""),
    ):
        result = await researcher.run_research(
            report="Performance report",
            track_id="track_openai",
            model_name="gpt-5.6-luna",
        )

    assert result is not None
    assert len(recorded_kwargs) > 0, "Expected chat.completions.create call during autoresearch extraction"
    assert recorded_kwargs[0].get("reasoning_effort") == "none", (
        f"Expected reasoning_effort='none' in kwargs, got {recorded_kwargs[0]}"
    )


@pytest.mark.asyncio
async def test_prompt_store_handles_missing_track_without_406():
    """Verify prompt_store handles queries for missing tracks cleanly."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query

    mock_res = MagicMock()
    mock_res.data = []
    mock_query.execute = AsyncMock(return_value=mock_res)

    with patch("autoresearch.prompt_store.get_async_supabase_client", return_value=mock_client):
        result = await prompt_store.get_active_prompt(
            prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
            is_backtest=False,
            track_id="track_openai",
        )

    assert result is None
