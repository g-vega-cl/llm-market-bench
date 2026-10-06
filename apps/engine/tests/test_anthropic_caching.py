from unittest.mock import AsyncMock, MagicMock

import pytest

from core.llm.analysis_pipeline import prompt_assembly
from core.llm.handlers import anthropic
from core.models import DecisionsResponse


@pytest.mark.asyncio
async def test_run_tool_loop_applies_prompt_caching():
    """Verify that Anthropic run_tool_loop applies explicit system cache breakpoint and automatic caching."""
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(type="text", text="Ready to trade.")]
    mock_resp.usage = MagicMock(
        input_tokens=150,
        output_tokens=25,
        cache_creation_input_tokens=5200,
        cache_read_input_tokens=0,
    )

    mock_client = MagicMock()
    mock_client.base_url = "https://api.anthropic.com/"
    mock_client.messages.create = AsyncMock(return_value=mock_resp)

    messages = [
        {"role": "system", "content": "You are a professional trader."},
        {"role": "user", "content": "Analyze AAPL with market data."},
    ]

    await anthropic.run_tool_loop(
        raw_client=mock_client,
        model_name="claude-haiku-4-5",
        messages=messages,
        max_tool_steps=1,
    )

    assert mock_client.messages.create.call_count == 1
    call_kwargs = mock_client.messages.create.call_args.kwargs

    # Top-level automatic caching
    assert call_kwargs.get("cache_control") == {"type": "ephemeral"}

    # System prompt explicit cache breakpoint
    system_param = call_kwargs.get("system")
    assert isinstance(system_param, list), "Anthropic system prompt must be a list of blocks for caching"
    assert len(system_param) == 1
    assert system_param[0] == {
        "type": "text",
        "text": "You are a professional trader.",
        "cache_control": {"type": "ephemeral"},
    }


def test_build_provider_extraction_args_anthropic_caching():
    """Verify that build_provider_extraction_args applies caching for Anthropic."""
    messages = [
        {"role": "system", "content": "System extraction prompt"},
        {"role": "user", "content": "Extract decisions"},
    ]

    args = prompt_assembly.build_provider_extraction_args(
        provider="anthropic",
        model_name="claude-haiku-4-5",
        messages=messages,
        response_model=DecisionsResponse,
    )

    assert args.get("cache_control") == {"type": "ephemeral"}
    system_param = args.get("system")
    assert isinstance(system_param, list)
    assert system_param[0] == {
        "type": "text",
        "text": "System extraction prompt",
        "cache_control": {"type": "ephemeral"},
    }


@pytest.mark.asyncio
async def test_run_tool_loop_minimax_does_not_apply_anthropic_cache_control():
    """Verify that MiniMax endpoint running through anthropic handler does not receive cache_control."""
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(type="text", text="MiniMax answer")]
    mock_resp.usage = MagicMock(input_tokens=100, output_tokens=10)

    mock_client = MagicMock()
    mock_client.base_url = "https://api.minimax.io/anthropic"
    mock_client.messages.create = AsyncMock(return_value=mock_resp)

    messages = [
        {"role": "system", "content": "You are MiniMax."},
        {"role": "user", "content": "Evaluate portfolio."},
    ]

    await anthropic.run_tool_loop(
        raw_client=mock_client,
        model_name="MiniMax-M3",
        messages=messages,
        max_tool_steps=1,
    )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "cache_control" not in call_kwargs
    assert isinstance(call_kwargs.get("system"), str)


@pytest.mark.asyncio
async def test_discovery_agent_anthropic_uses_prompt_caching():
    """Verify that DiscoveryAgent's forced text completion applies caching for Anthropic."""
    from analysis.discovery_agent import DiscoveryAgent

    mock_client = MagicMock()
    mock_raw_client = MagicMock()
    mock_client.client = mock_raw_client

    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(type="text", text='[{"ticker": "NVDA", "reasoning": "AI momentum"}]')]
    mock_raw_client.messages.create = AsyncMock(return_value=mock_resp)

    agent = DiscoveryAgent(
        model_name="claude-haiku-4-5",
        client=mock_client,
    )

    messages = [
        {"role": "system", "content": "You are a stock discovery agent."},
        {"role": "user", "content": "Find high momentum tech stocks."},
    ]

    await agent._force_text_completion(messages)

    assert mock_raw_client.messages.create.call_count == 1
    kwargs = mock_raw_client.messages.create.call_args.kwargs
    assert kwargs.get("cache_control") == {"type": "ephemeral"}
    assert isinstance(kwargs.get("system"), list)
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}


@pytest.mark.asyncio
async def test_verification_anthropic_uses_prompt_caching():
    """Verify that verify_trading_decision sets prompt caching and aligned thinking budget for Anthropic."""
    from unittest.mock import patch

    from core.llm.verification import verify_trading_decision
    from core.models import DecisionObject, VerificationResult

    decision = DecisionObject(
        ticker="AAPL",
        signal="BUY",
        confidence=80.0,
        reasoning="Strong earnings growth",
        model_provider="anthropic",
        model_name="claude-haiku-4-5",
        source_id="test_source_1",
    )

    mock_instructor = MagicMock()
    mock_result = VerificationResult(
        status="APPROVED",
        verification_reasoning="Sound thesis",
        confidence_score=90,
    )
    mock_instructor.chat.completions.create = AsyncMock(return_value=mock_result)

    with (
        patch("core.llm.clients.CLIENT_FACTORIES", {"anthropic": lambda: mock_instructor}),
        patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock) as mock_loop,
        patch("execution.market_data.MarketDataManager.get_quote", new_callable=AsyncMock, return_value=None),
        patch("memory.store.retrieve_for_decision", return_value=""),
    ):
        result = await verify_trading_decision(
            decision=decision,
            portfolio_context="",
            aggregated_context="",
        )

        assert result.status == "APPROVED"
        assert mock_loop.call_args.kwargs.get("thinking_budget") == 1024
        create_args = mock_instructor.chat.completions.create.call_args.kwargs
        assert create_args.get("cache_control") == {"type": "ephemeral"}
        assert create_args.get("thinking") == {"type": "enabled", "budget_tokens": 1024}
        assert isinstance(create_args.get("system"), list)
        assert create_args["system"][0]["cache_control"] == {"type": "ephemeral"}
