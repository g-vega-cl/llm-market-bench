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


def test_build_schema_hint_handles_pydantic_v2_classes():
    """build_schema_hint must inspect Pydantic v2 model_fields and never return '{}' for response classes."""
    from core.models import MacroEventsResponse, TradingDecisionsResponse

    trading_hint = prompt_assembly.build_schema_hint(TradingDecisionsResponse)
    macro_hint = prompt_assembly.build_schema_hint(MacroEventsResponse)
    combined_hint = prompt_assembly.build_schema_hint(DecisionsResponse)

    assert trading_hint != "{}"
    assert '"decisions"' in trading_hint
    assert '"macro_events"' not in trading_hint
    assert macro_hint != "{}"
    assert '"macro_events"' in macro_hint
    assert '"decisions"' not in macro_hint
    assert combined_hint != "{}"
    assert '"decisions"' in combined_hint
    assert '"macro_events"' in combined_hint


@pytest.mark.asyncio
async def test_minimax_extraction_preserves_context_and_uses_json_budget():
    """MiniMax extraction must preserve initial context/source_ids, raise token budget, and strip tool-sequence conflicts."""
    from core.models import TradingDecisionsResponse

    ledger_and_menu = (
        "CURRENT DATE CONTEXT: 2026-11-19\n"
        "Portfolio Cash: $10,000.00\n"
        "Source ID: news_macro_axios_com_82741e97 | Subject: Fed in focus\n"
        "\n\n=== Tool Execution History ===\n"
        "[Tool Result]: get_portfolio_ledger -> Cash: $10,000.00\n"
        "[Tool Result]: get_todays_news_menu -> news_macro_axios_com_82741e97\n"
    )
    middle_noise = "X" * 70000
    tail_indicators = "\n[Tool Result]: Technical Indicators for WMT: Price $125.63, RSI 61.2\n"
    long_history = ledger_and_menu + middle_noise + tail_indicators

    fake_client = MagicMock()
    fake_client.chat = AsyncMock(return_value={"content": json.dumps({"decisions": []}), "finish_reason": "stop"})
    fake_client.close = AsyncMock()

    conflicting_system = "6. SEQUENCE RULE: Do NOT output your final decisions JSON until you have FIRST executed all required tool calls."

    with patch("core.llm.minimax.MiniMaxClient", return_value=fake_client):
        await response_parsing.extract_with_minimax_openai(
            messages=[
                {"role": "system", "content": conflicting_system},
                {"role": "user", "content": long_history},
            ],
            model_name="MiniMax-M3.1-Flash",
            response_model=TradingDecisionsResponse,
            schema_hint=prompt_assembly.build_schema_hint(TradingDecisionsResponse),
        )

    call_kwargs = fake_client.chat.call_args.kwargs
    sent_messages = call_kwargs["messages"]
    sent_system = sent_messages[0]["content"]
    sent_user = sent_messages[1]["content"]

    assert "SEQUENCE RULE" not in sent_system
    assert "news_macro_axios_com_82741e97" in sent_user
    assert "Technical Indicators for WMT" in sent_user
    assert call_kwargs["max_completion_tokens"] >= 32768
    assert call_kwargs.get("response_format") == {"type": "json_object"}


@pytest.mark.asyncio
async def test_minimax_extraction_retries_once_on_validation_failure():
    """MiniMax extraction should retry once with schema feedback when attempt 1 fails parsing."""
    from core.models import TradingDecisionsResponse

    fake_client = MagicMock()
    fake_client.chat = AsyncMock(
        side_effect=[
            {"content": '{"decisions": "invalid"}', "finish_reason": "stop", "usage": {"output_tokens": 100}},
            {"content": json.dumps({"decisions": VALID_PAYLOAD["decisions"]}), "finish_reason": "stop"},
        ]
    )
    fake_client.close = AsyncMock()

    with patch("core.llm.minimax.MiniMaxClient", return_value=fake_client):
        wrapper = await response_parsing.extract_with_minimax_openai(
            messages=[{"role": "user", "content": "context"}],
            model_name="MiniMax-M3.1-Flash",
            response_model=TradingDecisionsResponse,
            schema_hint=prompt_assembly.build_schema_hint(TradingDecisionsResponse),
        )

    assert fake_client.chat.await_count == 2
    agg = response_parsing.aggregate_response_blocks(wrapper, TradingDecisionsResponse)
    assert len(agg.decisions) == 1
    assert agg.decisions[0].ticker == "XLV"


def test_create_fallback_model_inspects_pydantic_v2_fields():
    """create_fallback_model must instantiate empty response models via model_fields."""
    from core.models import MacroEventsResponse, TradingDecisionsResponse

    t = response_parsing.create_fallback_model(TradingDecisionsResponse)
    m = response_parsing.create_fallback_model(MacroEventsResponse)
    assert t.decisions == []
    assert m.macro_events == []
