"""Tests for DeepSeek tool-call narration and MiniMax empty/thinking-tag fixes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.analysis import _analyze_with_minimax
from core.llm.handlers import deepseek


@pytest.mark.asyncio
async def test_minimax_think_tag_strip_success():
    """Verify that _analyze_with_minimax strips <think> tags and successfully parses the JSON."""
    raw_response = (
        "<think>\n"
        "The user wants me to output JSON. Let's think about {"
        '  "reason": "We should check AAPL"\n'
        "}.\n"
        "</think>\n"
        "{\n"
        '  "decisions": [\n'
        "    {\n"
        '      "signal": "BUY",\n'
        '      "confidence": 90,\n'
        '      "reasoning": "Strong signal",\n'
        '      "ticker": "AAPL",\n'
        '      "catalyst_type": "EARNINGS",\n'
        '      "catalyst_duration": "SHORT_TERM",\n'
        '      "source_id": "s1",\n'
        '      "allocation_percentage": 10\n'
        "    }\n"
        "  ],\n"
        '  "macro_events": []\n'
        "}"
    )

    from core.llm.minimax import MiniMaxClient

    mock_chat_response = {
        "content": raw_response,
        "model": "MiniMax-M3",
        "finish_reason": "stop",
        "usage": {"input_tokens": 10, "output_tokens": 50},
        "processing_time_ms": 100,
    }

    with patch("core.config.MINIMAX_API_KEY", "fake-key"):
        with patch.object(MiniMaxClient, "chat", new=AsyncMock(return_value=mock_chat_response)):
            with patch.object(MiniMaxClient, "close", new=AsyncMock()):
                result = await _analyze_with_minimax(
                    model_name="MiniMax-M3",
                    chunks=[{"source_id": "s1", "content": "News."}],
                )
                assert len(result.decisions) == 1
                assert result.decisions[0].ticker == "AAPL"
                assert result.decisions[0].signal == "BUY"


@pytest.mark.asyncio
async def test_minimax_unclosed_think_tag_strip_success():
    """Verify that _analyze_with_minimax handles unclosed <think> tags gracefully (e.g. on token cutoff)."""
    raw_response = "<think>\nThinking about AAPL..."

    from core.llm.minimax import MiniMaxClient

    mock_chat_response = {
        "content": raw_response,
        "model": "MiniMax-M3",
        "finish_reason": "length",
        "usage": {"input_tokens": 10, "output_tokens": 50},
        "processing_time_ms": 100,
    }

    with patch("core.config.MINIMAX_API_KEY", "fake-key"):
        with patch.object(MiniMaxClient, "chat", new=AsyncMock(return_value=mock_chat_response)):
            with patch.object(MiniMaxClient, "close", new=AsyncMock()):
                result = await _analyze_with_minimax(
                    model_name="MiniMax-M3",
                    chunks=[{"source_id": "s1", "content": "News."}],
                )
                assert result.decisions == []
                assert result.macro_events == []


@pytest.mark.asyncio
async def test_minimax_empty_and_none_content_handling():
    """Verify that _analyze_with_minimax handles None or empty content without throwing errors."""
    from core.llm.minimax import MiniMaxClient

    # Mock response with None content
    mock_chat_response = {
        "content": None,
        "model": "MiniMax-M3",
        "finish_reason": "stop",
        "usage": {"input_tokens": 10, "output_tokens": 0},
        "processing_time_ms": 100,
    }

    with patch("core.config.MINIMAX_API_KEY", "fake-key"):
        with patch.object(MiniMaxClient, "chat", new=AsyncMock(return_value=mock_chat_response)):
            with patch.object(MiniMaxClient, "close", new=AsyncMock()):
                result = await _analyze_with_minimax(
                    model_name="MiniMax-M3",
                    chunks=[{"source_id": "s1", "content": "News."}],
                )
                assert result.decisions == []
                assert result.macro_events == []


@pytest.mark.asyncio
async def test_deepseek_no_thinking_in_tool_loop():
    """Verify that DeepSeek handler does not enable thinking mode during the tool execution loop."""
    mock_resp = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = "Analysis complete."
    mock_msg.tool_calls = None
    mock_resp.choices = [MagicMock(message=mock_msg)]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    messages = [{"role": "user", "content": "Analyze AAPL"}]

    await deepseek.run_tool_loop(
        raw_client=mock_client,
        model_name="deepseek-v4-pro",
        messages=messages,
        provider="deepseek",
        max_tool_steps=1,
    )

    # Check the args passed to client.chat.completions.create
    called_args = mock_client.chat.completions.create.call_args[1]

    # Assert that thinking mode is NOT enabled in the tool loop args.
    assert "extra_body" not in called_args or "thinking" not in called_args.get("extra_body", {})


@pytest.mark.asyncio
async def test_deepseek_thinking_in_final_extraction():
    """Verify that DeepSeek enables thinking mode during the final extraction step."""
    from core.llm.analysis import analyze_with_provider

    mock_resp = MagicMock()
    mock_resp.decisions = []
    mock_resp.macro_events = []

    mock_instructor_client = MagicMock()
    mock_instructor_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    # Patch client factory and tools to run quickly
    mock_factory = MagicMock(return_value=mock_instructor_client)
    with patch.dict("core.llm.clients.CLIENT_FACTORIES", {"deepseek": mock_factory}):
        with patch("core.llm.analysis.log_reasoning_trace", new=AsyncMock()):
            # Patch the tool loop so we don't make any actual API calls during verification
            with patch("core.llm.handlers.deepseek.run_tool_loop", new=AsyncMock()):
                with patch(
                    "core.llm.prompt_factory.PromptFactory.build_analysis_messages",
                    new=AsyncMock(
                        return_value=[{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
                    ),
                ):
                    await analyze_with_provider(
                        provider="deepseek",
                        model_name="deepseek-v4-pro",
                        chunks=[{"source_id": "s1", "content": "News."}],
                        context="",
                        portfolio_context="",
                        current_day_info="",
                        calendar_knowledge="",
                        macro_context="",
                    )

    # Check final extraction args passed to instructor
    called_args = mock_instructor_client.chat.completions.create.call_args[1]
    assert "extra_body" in called_args
    assert called_args["extra_body"].get("thinking", {}).get("type") == "enabled"
