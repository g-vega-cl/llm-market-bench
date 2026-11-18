"""Regression tests for provider-specific structured extraction.

Covers two production outages where models returned `decisions: []` not because
they declined to trade, but because the extraction step never produced JSON:

* DeepSeek imitated the synthetic `[Tool Call: ...]` markers that
  `prepare_messages_for_instructor` wrote into assistant turns.
* MiniMax's Anthropic-compatible endpoint emitted native
  `]<]minimax[>[<tool_call>` syntax instead of plain JSON.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.analysis_pipeline import prompt_assembly, response_parsing
from core.llm.handlers import deepseek
from core.models import DecisionsResponse

MINIMAX_NATIVE_JUNK = (
    ']<]minimax[>[<tool_call>]<]minimax[>[<invoke name="get_stock_quote">'
    "]<]minimax[>[<ticker>XLP]<]minimax[>[</ticker>]<]minimax[>[</invoke>"
    "]<]minimax[>[</tool_call>"
)

VALID_PAYLOAD = {
    "decisions": [
        {
            "ticker": "XLV",
            "signal": "HOLD",
            "confidence": 76,
            "reasoning": "Price above SMA20 and SMA50.",
            "catalyst_type": "TECHNICAL",
            "catalyst_duration": "MEDIUM_TERM",
            "source_id": "tool:get_technical_indicators_XLV",
        }
    ],
    "macro_events": [],
}


def _tool_loop_history() -> list[dict]:
    """A realistic DeepSeek tool-loop history ending in prose analysis."""
    return [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "newsletter batch"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "c1", "function": {"name": "get_stock_quote", "arguments": '{"ticker": "XLP"}'}}],
        },
        {"role": "tool", "tool_call_id": "c1", "content": "XLP price $91.20"},
        {"role": "assistant", "content": "Staples are holding up; I lean toward holding."},
    ]


def test_deepseek_prepare_messages_strips_tool_call_markers():
    """Assistant turns must not carry `[Tool Call: ...]` text the model can imitate."""
    cleaned = deepseek.prepare_messages_for_instructor(_tool_loop_history())

    for msg in cleaned:
        content = msg.get("content") or ""
        assert "[Tool Call:" not in content, f"tool-call marker leaked into {msg['role']} turn: {content!r}"

    # The tool-only assistant turn must be dropped entirely, not left empty.
    assistant_turns = [m for m in cleaned if m.get("role") == "assistant"]
    assert len(assistant_turns) == 1
    assert "holding" in assistant_turns[0]["content"]

    # Tool results are still preserved so the model keeps its evidence.
    assert any("XLP price" in (m.get("content") or "") for m in cleaned)


def test_deepseek_extraction_args_include_json_only_instruction():
    """The final extraction turn must forbid tools and restate the schema."""
    args = prompt_assembly.build_provider_extraction_args(
        provider="deepseek",
        model_name="deepseek-flash",
        messages=deepseek.prepare_messages_for_instructor(_tool_loop_history()),
        response_model=DecisionsResponse,
    )

    last = args["messages"][-1]
    assert last["role"] == "user"
    instruction = last["content"]
    assert "Do NOT call any tools" in instruction
    assert "raw JSON" in instruction
    assert "decisions" in instruction


@pytest.mark.asyncio
async def test_minimax_extraction_uses_openai_endpoint():
    """MiniMax extraction must go through the OpenAI-compatible client, not Instructor."""
    fake_chat = AsyncMock(return_value={"content": json.dumps(VALID_PAYLOAD), "finish_reason": "stop"})
    fake_client = MagicMock()
    fake_client.chat = fake_chat
    fake_client.close = AsyncMock()

    instructor_client = MagicMock()
    instructor_client.chat.completions.create = AsyncMock(side_effect=AssertionError("Instructor must not be used"))

    with patch("core.llm.minimax.MiniMaxClient", return_value=fake_client):
        wrapper = await response_parsing.extract_structured_response(
            client=instructor_client,
            final_args={
                "model": "MiniMax-M3.1-Flash",
                "messages": [
                    {"role": "system", "content": "system prompt"},
                    {"role": "user", "content": "flattened history"},
                ],
            },
            provider="minimax",
            model_name="MiniMax-M3.1-Flash",
            response_model=DecisionsResponse,
            schema_hint='{"decisions": []}',
            messages=[
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "flattened history"},
            ],
        )

    agg = response_parsing.aggregate_response_blocks(wrapper, DecisionsResponse)
    assert len(agg.decisions) == 1
    assert agg.decisions[0].ticker == "XLV"
    assert fake_chat.await_count == 1
    fake_client.close.assert_awaited()


@pytest.mark.asyncio
async def test_minimax_extraction_strips_native_tool_syntax():
    """Native MiniMax tool syntax must be stripped before JSON parsing."""
    content = MINIMAX_NATIVE_JUNK + "\n" + json.dumps(VALID_PAYLOAD)
    fake_client = MagicMock()
    fake_client.chat = AsyncMock(return_value={"content": content, "finish_reason": "stop"})
    fake_client.close = AsyncMock()

    with patch("core.llm.minimax.MiniMaxClient", return_value=fake_client):
        wrapper = await response_parsing.extract_structured_response(
            client=MagicMock(),
            final_args={"model": "MiniMax-M3.1-Flash", "messages": [{"role": "user", "content": "x"}]},
            provider="minimax",
            model_name="MiniMax-M3.1-Flash",
            response_model=DecisionsResponse,
            schema_hint='{"decisions": []}',
            messages=[{"role": "user", "content": "x"}],
        )

    agg = response_parsing.aggregate_response_blocks(wrapper, DecisionsResponse)
    assert len(agg.decisions) == 1
