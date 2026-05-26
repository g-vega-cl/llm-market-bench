"""Tests for Hard Tool Enforcement in analysis.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analysis.consensus import _is_vague_government_event
from core.llm.analysis import (
    _scan_history_for_tools,
    analyze_with_provider,
)
from core.models import DecisionObject, DecisionsResponse


@pytest.fixture
def mock_clients():
    """Mocks LLM clients and handlers."""
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        # Mock Instructor-wrapped client
        MagicMock()
        mock_client.chat.completions.create = AsyncMock()

        yield {"factory": mock_factory, "client": mock_client, "instructor": mock_client.chat.completions}


def test_scan_history_openai_format():
    """Verify scanning OpenAI-style message history for quantity tools."""
    messages = [
        {"role": "user", "content": "Sell AAPL"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {
                        "name": "calculate_sell_quantity",
                        "arguments": '{"ticker": "AAPL", "percentage": 50}',
                    },
                    "id": "call_1",
                },
                {
                    "function": {"name": "calculate_buy_quantity", "arguments": '{"ticker": "AAPL", "percentage": 20}'},
                    "id": "call_2",
                },
            ],
        },
    ]

    res = _scan_history_for_tools(messages, "AAPL")
    assert res["sell_tool_found"] is True
    assert res["buy_tool_found"] is True

    res_msft = _scan_history_for_tools(messages, "MSFT")
    assert res_msft["sell_tool_found"] is False
    assert res_msft["buy_tool_found"] is False


def test_scan_history_anthropic_format():
    """Verify scanning Anthropic-style message history for quantity tools."""
    messages = [
        {"role": "user", "content": "Sell TSLA"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me check..."},
                {
                    "type": "tool_use",
                    "name": "calculate_sell_quantity",
                    "input": {"ticker": "TSLA", "percentage": 100},
                    "id": "u1",
                },
            ],
        },
    ]

    res = _scan_history_for_tools(messages, "TSLA")
    assert res["sell_tool_found"] is True
    assert res["buy_tool_found"] is False


def test_scan_history_gemini_format():
    """Verify scanning Gemini-style native content history."""

    class MockFunctionCall:
        def __init__(self, name, args):
            self.name = name
            self.args = args

    class MockPart:
        def __init__(self, name, args):
            self.function_call = MockFunctionCall(name, args)

    class MockContent:
        def __init__(self, parts):
            self.parts = parts

    messages = [
        MockContent(
            [
                MockPart("calculate_buy_quantity", {"ticker": "GOOG", "percentage": 50}),
                MockPart("calculate_sell_quantity", {"ticker": "GOOG", "percentage": 100}),
            ]
        )
    ]

    res = _scan_history_for_tools(messages, "GOOG")
    assert res["buy_tool_found"] is True
    assert res["sell_tool_found"] is True


def test_scan_history_robust_matching():
    """Verify that ticker matching is robust to spaces and casing."""
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {
                        "name": "calculate_buy_quantity",
                        "arguments": '{"ticker": "  aapl  ", "percentage": 10}',
                    },
                    "id": "c1",
                }
            ],
        }
    ]

    res = _scan_history_for_tools(messages, "AAPL")
    assert res["buy_tool_found"] is True

    res_messy = _scan_history_for_tools(messages, " aapl ")
    assert res_messy["buy_tool_found"] is True


@pytest.mark.asyncio
async def test_analyze_with_provider_hard_enforcement(mock_clients):
    """Verify that analyze_with_provider correctly updates sell_tool_called."""
    mock_instructor = mock_clients["instructor"]

    mock_instructor.create.return_value = [
        DecisionsResponse(
            decisions=[
                DecisionObject(
                    signal="SELL",
                    ticker="AAPL",
                    confidence=90,
                    reasoning="Test",
                    source_id="s1",
                    sell_tool_called=True,
                    quantity=10,
                )
            ],
            macro_events=[],
        )
    ]

    with (
        patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock),
        patch("core.llm.logger.log_reasoning_trace", new_callable=AsyncMock),
    ):
        resp = await analyze_with_provider(
            provider="openai", model_name="gpt-4", chunks=[{"source_id": "s1", "content": "..."}]
        )

    assert resp.decisions[0].ticker == "AAPL"
    assert resp.decisions[0].sell_tool_called is False


def test_is_vague_government_event_true_for_generic_names():
    """Consensus helper should flag generic government event names as vague."""
    assert _is_vague_government_event("Ongoing Legislative Policy Developments") is True
    assert _is_vague_government_event("Government Policy Update") is True
    assert _is_vague_government_event("Government Policy Structural Update") is True
    assert _is_vague_government_event("Policy Structural Update") is True
    assert _is_vague_government_event("VAGUE_GOVERNMENT_EVENT") is True


def test_is_vague_government_event_false_for_specific_names():
    """Consensus helper should NOT flag specific government event names."""
    assert _is_vague_government_event("US Farm Bill 2026 Agri-Tech Push") is False
    assert _is_vague_government_event("CHIPS Act Expansion") is False
    assert _is_vague_government_event("EU Green Hydrogen Act") is False
    assert _is_vague_government_event("Japan GX Transformation Bonds") is False
    assert _is_vague_government_event("Fed Rate Cut Cycle") is False


def test_is_vague_government_event_false_for_non_policy_events():
    """Non-policy events should never be flagged as vague government."""
    assert _is_vague_government_event("AI Demand Surge", "tech sector rallies") is False
    assert _is_vague_government_event("Earnings Season Begins") is False
    assert _is_vague_government_event("Oil Supply Disruption") is False


@pytest.mark.asyncio
async def test_analyze_with_provider_hard_enforcement_anthropic(mock_clients):
    """Verify that analyze_with_provider correctly verifies Anthropic tool calls in history."""
    mock_instructor = mock_clients["instructor"]

    # Mock instructor response to return a SELL decision for GXO
    mock_instructor.create.return_value = [
        DecisionsResponse(
            decisions=[
                DecisionObject(
                    signal="SELL",
                    ticker="GXO",
                    confidence=90,
                    reasoning="Test",
                    source_id="s1",
                    sell_tool_called=True,
                    quantity=10,
                )
            ],
            macro_events=[],
        )
    ]

    # Mock tool loop to simulate a successful Anthropic run_tool_loop execution
    # that calls the sell tool.
    async def fake_anthropic_run_tool_loop(raw_client, model_name, messages, **kwargs):
        messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "calculate_sell_quantity",
                        "input": {"ticker": "GXO", "percentage": 100},
                        "id": "call_anthropic_1",
                    }
                ],
            }
        )

    with (
        patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock) as mock_run_loop,
        patch("core.llm.logger.log_reasoning_trace", new_callable=AsyncMock),
    ):
        mock_run_loop.side_effect = fake_anthropic_run_tool_loop

        resp = await analyze_with_provider(
            provider="anthropic",
            model_name="claude-3-5-sonnet",
            chunks=[{"source_id": "s1", "content": "..."}],
            portfolio_context="- GXO: 100 shares",  # To satisfy ownership validation
        )

    # In a correct implementation, sell_tool_called should remain True.
    # In a broken (flattened messages passed to scan) implementation, it will be False.
    assert resp.decisions[0].ticker == "GXO"
    assert resp.decisions[0].sell_tool_called is True


@pytest.mark.asyncio
async def test_analyze_with_provider_hard_enforcement_logs_diagnostics(mock_clients, caplog):
    """Verify that analyze_with_provider logs diagnostic info (messages, tools called) on hard enforcement failure."""
    import logging

    mock_instructor = mock_clients["instructor"]

    # Mock instructor response to return a BUY decision for AAPL
    mock_instructor.create.return_value = [
        DecisionsResponse(
            decisions=[
                DecisionObject(
                    signal="BUY",
                    ticker="AAPL",
                    confidence=90,
                    reasoning="Test BUY",
                    source_id="s2",
                    buy_tool_called=True,
                    quantity=5,
                )
            ],
            macro_events=[],
        )
    ]

    # Mock tool loop to call stock quote instead of the required buy quantity tool
    async def fake_openai_run_tool_loop(raw_client, model_name, messages, *args, **kwargs):
        messages.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_stock_quote",
                            "arguments": '{"ticker": "AAPL"}',
                        },
                        "id": "call_diagnostics_1",
                    }
                ],
            }
        )

    with (
        patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock) as mock_run_loop,
        patch("core.llm.logger.log_reasoning_trace", new_callable=AsyncMock),
    ):
        mock_run_loop.side_effect = fake_openai_run_tool_loop

        with caplog.at_level(logging.WARNING, logger="engine"):
            await analyze_with_provider(
                provider="openai",
                model_name="gpt-4",
                chunks=[{"source_id": "s2", "content": "..."}],
            )

    # Assert that the warning logs contain the diagnostic information
    warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) > 0

    diagnostic_warning = None
    for w in warnings:
        if "HARD ENFORCEMENT" in w and "AAPL" in w:
            diagnostic_warning = w
            break

    assert diagnostic_warning is not None
    assert "Total messages in history:" in diagnostic_warning or "Total messages:" in diagnostic_warning
    assert "Tools called:" in diagnostic_warning
    assert "get_stock_quote" in diagnostic_warning
