"""Unit tests for the execution trace attribution module."""

from attribution.trace import (
    attach_trace_to_decisions,
    build_execution_trace,
    extract_tool_trace_from_messages,
)
from core.models import DecisionObject


def test_extract_tool_trace_openai_format():
    """Extract tool calls from OpenAI style message dictionaries."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze NVDA and AAPL."},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "get_stock_quote",
                        "arguments": '{"ticker": "NVDA"}',
                    },
                },
                {
                    "id": "call_2",
                    "function": {
                        "name": "calculate_buy_quantity",
                        "arguments": '{"ticker": "NVDA", "percentage": 15}',
                    },
                },
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": '{"price": 118.20}'},
        {"role": "tool", "tool_call_id": "call_2", "content": '{"quantity": 45}'},
    ]

    tools = extract_tool_trace_from_messages(messages)
    assert len(tools) == 2
    assert tools[0]["tool"] == "get_stock_quote"
    assert tools[0]["args"] == {"ticker": "NVDA"}
    assert tools[0]["ticker"] == "NVDA"

    assert tools[1]["tool"] == "calculate_buy_quantity"
    assert tools[1]["args"] == {"ticker": "NVDA", "percentage": 15}
    assert tools[1]["ticker"] == "NVDA"


def test_extract_tool_trace_anthropic_format():
    """Extract tool calls from Anthropic style content block lists."""
    messages = [
        {"role": "user", "content": "Review market data."},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me check the price history and macro options."},
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "get_price_history",
                    "input": {"ticker": "TSLA", "days": 14},
                },
            ],
        },
    ]

    tools = extract_tool_trace_from_messages(messages)
    assert len(tools) == 1
    assert tools[0]["tool"] == "get_price_history"
    assert tools[0]["args"] == {"ticker": "TSLA", "days": 14}
    assert tools[0]["ticker"] == "TSLA"


def test_extract_tool_trace_empty():
    """Return empty list when no tool calls were made."""
    messages = [
        {"role": "system", "content": "You are a trading agent."},
        {"role": "user", "content": "Hold cash today."},
        {"role": "assistant", "content": "Understood."},
    ]
    tools = extract_tool_trace_from_messages(messages)
    assert tools == []


def test_build_execution_trace_multi_chunk():
    """Compile multi-chunk context and tool traces into a complete ExecutionTrace."""
    chunks = [
        {
            "source_id": "news_bloomberg_01",
            "sender": "Bloomberg Markets <news@bloomberg.com>",
            "subject": "Hyperscaler Capex Report",
            "content": "Data center spending jumps 40%...",
        },
        {
            "source_id": "news_reuters_02",
            "sender": "Reuters Wire",
            "subject": "Semiconductor Supply Chain Easing",
            "content": "Packaging backlogs reduced across foundries...",
        },
    ]

    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_stock_quote",
                        "arguments": '{"ticker": "NVDA"}',
                    }
                }
            ],
        }
    ]

    trace = build_execution_trace(chunks, messages)

    assert trace["active_source_ids"] == ["news_bloomberg_01", "news_reuters_02"]
    assert len(trace["newsletters"]) == 2
    assert trace["newsletters"][0]["source_id"] == "news_bloomberg_01"
    assert trace["newsletters"][0]["sender"] == "Bloomberg Markets <news@bloomberg.com>"
    assert trace["newsletters"][0]["subject"] == "Hyperscaler Capex Report"

    assert len(trace["tools_called"]) == 1
    assert trace["tools_called"][0]["tool"] == "get_stock_quote"
    assert trace["tools_called"][0]["ticker"] == "NVDA"
    assert "captured_at" in trace


def test_attach_trace_to_decisions():
    """Attach the compiled trace to all decision objects in a batch."""
    decisions = [
        DecisionObject(
            signal="BUY",
            confidence=90,
            reasoning="NVDA demand intact",
            ticker="NVDA",
            source_id="news_bloomberg_01",
        ),
        DecisionObject(
            signal="HOLD",
            confidence=60,
            reasoning="Waiting for earnings",
            ticker="AAPL",
            source_id="news_reuters_02",
        ),
    ]

    trace = {
        "active_source_ids": ["news_bloomberg_01", "news_reuters_02"],
        "newsletters": [{"source_id": "news_bloomberg_01", "sender": "Bloomberg", "subject": "Capex"}],
        "tools_called": [{"tool": "get_stock_quote", "args": {"ticker": "NVDA"}, "ticker": "NVDA"}],
        "captured_at": "2026-09-20T23:15:00Z",
    }

    attach_trace_to_decisions(decisions, trace)

    for d in decisions:
        assert d.metadata is not None
        assert d.metadata.get("execution_trace") == trace
