"""Tests verifying MiniMax-M3 is wired through the Anthropic SDK
pointed at MiniMax's Anthropic-compatible base URL.

These tests pin down the architectural decision: MiniMax-M3 uses the Anthropic
API format (via the Anthropic SDK), not the OpenAI-compatible format. The
OpenAI-format MiniMaxClient (core/llm/minimax.py) is reserved for auxiliary
flows (market_feeling, sector_predictor) that don't need tool calling.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


@pytest.fixture(autouse=True)
def mock_active_prompt():
    with patch("autoresearch.prompt_store.get_active_prompt", return_value=None):
        yield


def test_get_minimax_client_uses_anthropic_sdk():
    """get_minimax_client must construct AsyncAnthropic (not AsyncOpenAI)
    pointed at MiniMax's Anthropic-compatible endpoint."""
    from core.llm import clients

    with (
        patch("core.llm.clients.AsyncAnthropic") as mock_anthropic,
        patch("core.llm.clients.AsyncOpenAI") as mock_openai,
        patch("core.llm.clients.instructor.from_anthropic") as mock_from_anthropic,
        patch("core.llm.clients.instructor.from_openai") as mock_from_openai,
    ):
        mock_from_anthropic.return_value = "MOCKED_INSTRUCTOR_CLIENT"
        clients.get_minimax_client(api_key="test-key")

        # AsyncAnthropic was called with the anthropic base URL
        mock_anthropic.assert_called_once()
        kwargs = mock_anthropic.call_args.kwargs
        assert kwargs["api_key"] == "test-key"
        assert kwargs["base_url"] == "https://api.minimax.io/anthropic"
        assert "timeout" in kwargs

        # AsyncOpenAI was NOT called (MiniMax no longer uses OpenAI SDK for analysis)
        mock_openai.assert_not_called()

        # instructor.from_anthropic was used to wrap the client
        mock_from_anthropic.assert_called_once()
        import instructor

        assert mock_from_anthropic.call_args.kwargs.get("mode") == instructor.Mode.ANTHROPIC_JSON
        mock_from_openai.assert_not_called()


def test_get_minimax_client_base_url_is_overridable():
    """MINIMAX_ANTHROPIC_BASE_URL config var overrides the default base URL."""
    from core import config
    from core.llm import clients

    with (
        patch.object(config, "MINIMAX_ANTHROPIC_BASE_URL", "https://custom.example/anthropic"),
        patch("core.llm.clients.AsyncAnthropic") as mock_anthropic,
        patch("core.llm.clients.instructor.from_anthropic", return_value="MOCK"),
    ):
        clients.get_minimax_client(api_key="test-key")
        assert mock_anthropic.call_args.kwargs["base_url"] == "https://custom.example/anthropic"


def test_analyze_with_provider_minimax_dispatches_to_anthropic_handler():
    """When provider='minimax', the tool loop dispatch must route through
    handlers.anthropic.run_tool_loop, NOT handlers.openai.run_tool_loop."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from core.config import MINIMAX_MODEL
    from core.llm import analysis as analysis_mod
    from core.models import DecisionsResponse

    decisions_resp = DecisionsResponse(
        decisions=[],
        macro_events=[],
    )

    mock_client = MagicMock()
    mock_client.client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=decisions_resp)
    mock_factory = MagicMock(return_value=mock_client)

    with (
        patch("core.llm.clients.CLIENT_FACTORIES", {"minimax": mock_factory}),
        patch("core.llm.handlers.anthropic.run_tool_loop", new=AsyncMock()) as mock_anthro_loop,
        patch("core.llm.handlers.openai.run_tool_loop", new=AsyncMock()) as mock_openai_loop,
    ):
        import asyncio

        asyncio.run(
            analysis_mod.analyze_with_provider(
                provider="minimax",
                model_name=MINIMAX_MODEL,
                chunks=[{"source_id": "s1", "content": "Test news"}],
                context="",
                portfolio_context="Cash: $10k",
                current_day_info="",
                calendar_knowledge="",
                macro_context="",
            )
        )

        # Anthropic tool loop was called; OpenAI tool loop was not
        mock_anthro_loop.assert_called_once()
        mock_openai_loop.assert_not_called()


@pytest.mark.asyncio
async def test_minimax_parameters_and_system_message():
    """Verify that provider='minimax' correctly passes max_tokens and system message to the Anthropic client."""
    from core.llm import analysis as analysis_mod
    from core.models import DecisionsResponse

    decisions_resp = DecisionsResponse(decisions=[], macro_events=[])
    mock_client = MagicMock()
    mock_client.client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=decisions_resp)
    mock_factory = MagicMock(return_value=mock_client)

    with (
        patch("core.llm.clients.CLIENT_FACTORIES", {"minimax": mock_factory}),
        patch("core.llm.handlers.anthropic.run_tool_loop", new=AsyncMock()),
    ):
        await analysis_mod.analyze_with_provider(
            provider="minimax",
            model_name="MiniMax-M3",
            chunks=[{"source_id": "s1", "content": "Test news"}],
            context="",
            portfolio_context="Cash: $10k",
            current_day_info="",
            calendar_knowledge="",
            macro_context="",
        )

        assert mock_client.chat.completions.create.called
        kwargs = mock_client.chat.completions.create.call_args.kwargs

        assert "max_tokens" in kwargs
        assert kwargs["max_tokens"] == 32000
        assert "system" in kwargs
        assert kwargs["system"] is not None


@pytest.mark.asyncio
async def test_minimax_retry_routes_to_anthropic_handler():
    """Verify that when a tool retry occurs for minimax, it routes to the anthropic handler, not openai."""
    from core.llm import analysis as analysis_mod
    from core.models import DecisionObject, DecisionsResponse

    decisions_resp_with_buy = DecisionsResponse(
        decisions=[
            DecisionObject(
                ticker="MU",
                signal="BUY",
                confidence=90,
                reasoning="Buy MU because of semiconductor demand.",
                catalyst_type="EARNINGS",
                catalyst_duration="SHORT_TERM",
                source_id="s1",
                allocation_percentage=10,
                buy_tool_called=False,
            )
        ],
        macro_events=[],
    )

    mock_client = MagicMock()
    mock_client.client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[decisions_resp_with_buy, DecisionsResponse(decisions=[], macro_events=[])]
    )
    mock_factory = MagicMock(return_value=mock_client)

    with (
        patch("core.llm.clients.CLIENT_FACTORIES", {"minimax": mock_factory}),
        patch("core.llm.handlers.anthropic.run_tool_loop", new=AsyncMock()) as mock_anthro_loop,
        patch("core.llm.handlers.openai.run_tool_loop", new=AsyncMock()) as mock_openai_loop,
    ):
        await analysis_mod.analyze_with_provider(
            provider="minimax",
            model_name="MiniMax-M3",
            chunks=[{"source_id": "s1", "content": "Test news"}],
            context="",
            portfolio_context="Cash: $10k",
            current_day_info="",
            calendar_knowledge="",
            macro_context="",
        )

        assert mock_anthro_loop.call_count == 2
        mock_openai_loop.assert_not_called()


@pytest.mark.asyncio
async def test_minimax_system_prompt_nudge():
    """Verify that provider='minimax' prepends the system protocol nudge to the system message."""
    from core.llm.prompt_factory import PromptFactory

    messages = await PromptFactory.build_analysis_messages(
        provider="minimax",
        enable_web_search=False,
        market_data_block="DATA",
        owner_id="MiniMax-M3",
        portfolio_context="CASH",
        context="CONTEXT",
        news_content="NEWS",
        current_day_info="TODAY",
        calendar_knowledge="CALENDAR",
        macro_context="MACRO",
        held_tickers_list=["AAPL"],
    )

    # First message in history should be the system message with the special prefix
    assert messages[0]["role"] == "system"
    system_content = messages[0]["content"]
    assert "=== SYSTEM PROTOCOL: MANDATORY TOOL USE FOR MINIMAX ===" in system_content

    # Verify standard provider (e.g. openai) does NOT get prepended with the minimax nudge
    openai_messages = await PromptFactory.build_analysis_messages(
        provider="openai",
        enable_web_search=False,
        market_data_block="DATA",
        owner_id="gpt-5.4-nano",
        portfolio_context="CASH",
        context="CONTEXT",
        news_content="NEWS",
        current_day_info="TODAY",
        calendar_knowledge="CALENDAR",
        macro_context="MACRO",
        held_tickers_list=["AAPL"],
    )
    assert openai_messages[0]["role"] == "system"
    assert "=== SYSTEM PROTOCOL: MANDATORY TOOL USE FOR MINIMAX ===" not in openai_messages[0]["content"]


@pytest.mark.asyncio
async def test_minimax_history_flattening_to_single_user_message():
    """Verify that provider='minimax' flattens multi-turn tool history into a single user message."""
    from core.llm import analysis as analysis_mod
    from core.models import DecisionsResponse

    decisions_resp = DecisionsResponse(decisions=[], macro_events=[])

    mock_client = MagicMock()
    mock_client.client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=decisions_resp)
    mock_factory = MagicMock(return_value=mock_client)

    async def mock_run_tool_loop(client, model, messages, **kwargs):
        messages.append({
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Analyzing the situation."},
                {"type": "tool_use", "id": "t1", "name": "calculate_buy_quantity", "input": {"ticker": "SMH", "percentage": 14}}
            ]
        })
        messages.append({
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "Success"}]
        })
        messages.append({
            "role": "assistant",
            "content": [{"type": "text", "text": "Final analysis complete."}]
        })

    with (
        patch("core.llm.clients.CLIENT_FACTORIES", {"minimax": mock_factory}),
        patch("core.llm.handlers.anthropic.run_tool_loop", new=mock_run_tool_loop),
    ):
        await analysis_mod.analyze_with_provider(
            provider="minimax",
            model_name="MiniMax-M3",
            chunks=[{"source_id": "s1", "content": "Test news"}],
            context="",
            portfolio_context="Cash: $10k",
            current_day_info="",
            calendar_knowledge="",
            macro_context="",
        )

        assert mock_client.chat.completions.create.called
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs

        # Verify that system prompt is extracted correctly
        assert "=== SYSTEM PROTOCOL: MANDATORY TOOL USE FOR MINIMAX ===" in call_kwargs["system"]

        # Verify messages list is flattened to exactly 1 user message
        flat_messages = call_kwargs["messages"]
        assert len(flat_messages) == 1
        user_msg = flat_messages[0]
        assert user_msg["role"] == "user"

        # Verify natural language representation of tool use and tool result is present
        assert "(Executed tool calculate_buy_quantity with arguments: {'ticker': 'SMH', 'percentage': 14})" in user_msg["content"]
        assert "(Tool returned result: Success)" in user_msg["content"]
        assert "[Assistant]: Final analysis complete." in user_msg["content"]

