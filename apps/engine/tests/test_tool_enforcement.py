"""Tests for Hard Tool Enforcement in analysis.py."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.llm.analysis import analyze_with_provider, _scan_history_for_tools, _ensure_government_incentive_events
from core.models import DecisionsResponse, DecisionObject, MacroEvent

@pytest.fixture
def mock_clients():
    """Mocks LLM clients and handlers."""
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory
        
        # Mock Instructor-wrapped client
        mock_instructor_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        
        yield {
            "factory": mock_factory,
            "client": mock_client,
            "instructor": mock_client.chat.completions
        }

def test_scan_history_openai_format():
    """Verify scanning OpenAI-style message history."""
    messages = [
        {"role": "user", "content": "Sell AAPL"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {"name": "calculate_sell_quantity", "arguments": '{"ticker": "AAPL", "percentage": 50}'},
                    "id": "call_1"
                },
                {
                    "function": {"name": "get_stock_quote", "arguments": '{"ticker": "AAPL"}'},
                    "id": "call_2"
                }
            ]
        }
    ]
    
    res = _scan_history_for_tools(messages, "AAPL")
    assert res["quote_found"] is True
    assert res["sell_tool_found"] is True
    
    res_msft = _scan_history_for_tools(messages, "MSFT")
    assert res_msft["quote_found"] is False

def test_scan_history_anthropic_format():
    """Verify scanning Anthropic-style message history."""
    messages = [
        {"role": "user", "content": "Sell TSLA"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me check..."},
                {"type": "tool_use", "name": "get_stock_quote", "input": {"ticker": "TSLA"}, "id": "u1"}
            ]
        }
    ]
    
    res = _scan_history_for_tools(messages, "TSLA")
    assert res["quote_found"] is True
    assert res["sell_tool_found"] is False # Sell tool missing

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
        MockContent([
            MockPart("get_stock_quote", {"ticker": "GOOG"}),
            MockPart("calculate_sell_quantity", {"ticker": "GOOG", "percentage": 100})
        ])
    ]
    
    res = _scan_history_for_tools(messages, "GOOG")
    assert res["quote_found"] is True
    assert res["sell_tool_found"] is True

def test_scan_history_robust_matching():
    """Verify that ticker matching is robust to spaces and casing."""
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {"name": "get_stock_quote", "arguments": '{"ticker": "  aapl  "}'},
                    "id": "c1"
                }
            ]
        }
    ]
    
    # Matching with clean ticker
    res = _scan_history_for_tools(messages, "AAPL")
    assert res["quote_found"] is True
    
    # Matching with messy ticker
    res_messy = _scan_history_for_tools(messages, " aapl ")
    assert res_messy["quote_found"] is True

@pytest.mark.asyncio
async def test_analyze_with_provider_government_enforcement(mock_clients, caplog):
    """Verify that government incentive enforcement triggers warnings."""
    mock_instructor = mock_clients["instructor"]
    
    # Return a response with gov content but NO macro events
    mock_instructor.create.return_value = [DecisionsResponse(
        decisions=[],
        macro_events=[]
    )]
    
    chunks = [{"source_id": "gov_1", "content": "The US Congress passed a new subsidy bill for AI."}]
    
    with patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock), \
         patch("core.llm.logger.log_reasoning_trace", new_callable=AsyncMock):
        await analyze_with_provider(
            provider="openai",
            model_name="gpt-4",
            chunks=chunks
        )
    
    assert "GOVERNMENT INCENTIVE ENFORCEMENT" in caplog.text
    assert "contains government policy content but NO macro_events were generated" in caplog.text

@pytest.mark.asyncio
async def test_analyze_with_provider_hard_enforcement(mock_clients):
    """Verify that analyze_with_provider correctly updates sell_tool_called."""
    # Setup: Agent claims to have called sell tool but history is empty
    mock_instructor = mock_clients["instructor"]
    
    # DecisionsResponse returned by Instructor
    mock_instructor.create.return_value = [DecisionsResponse(
        decisions=[
            DecisionObject(
                signal="SELL",
                ticker="AAPL",
                confidence=90,
                reasoning="Test",
                source_id="s1",
                sell_tool_called=True, # AGENT CLAIMS TRUE
                quantity=10
            )
        ],
        macro_events=[]
    )]
    
    # Mock handlers to not add any tools to messages
    with patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock), \
         patch("core.llm.logger.log_reasoning_trace", new_callable=AsyncMock):
        resp = await analyze_with_provider(
            provider="openai",
            model_name="gpt-4",
            chunks=[{"source_id": "s1", "content": "..."}]
        )
        
    # Verify that the final decision has sell_tool_called=False because history was empty
    assert resp.decisions[0].ticker == "AAPL"
    assert resp.decisions[0].sell_tool_called is False # UPDATED BY HARD ENFORCEMENT


def test_government_incentive_helper_marks_existing_macro_event():
    """Verify that a policy-related macro event gets auto-flagged when the model misses it."""
    response = DecisionsResponse(
        decisions=[],
        macro_events=[
            MacroEvent(
                event_name="US Farm Bill 2026 Agri-Tech Push",
                impact="BULLISH",
                catalyst_type="REGULATORY",
                is_ongoing=False,
                is_future_catalyst=False,
                historical_parallel=None,
                is_government_incentive=False,
                expiry_date="2026-12-31",
                importance_score=8,
                confidence=88,
                reasoning="Congress advanced new subsidy support for precision agriculture.",
                scenario_analysis="Scenario A: Passage -> Trading Plan: Buy DE.",
                source_id="gov_1",
                model_provider="openai",
                model_name="gpt-4"
            )
        ]
    )

    _ensure_government_incentive_events(
        response,
        [{"source_id": "gov_1", "content": "The US Congress passed a new subsidy bill for AI."}],
        "openai",
        "gpt-4"
    )

    assert response.macro_events[0].is_government_incentive is True


def test_government_incentive_helper_synthesizes_fallback_event():
    """Verify that policy-heavy chunks still yield a flagged event if the model returns none."""
    response = DecisionsResponse(decisions=[], macro_events=[])

    _ensure_government_incentive_events(
        response,
        [{"source_id": "gov_2", "content": "The EU approved a new green hydrogen subsidy package."}],
        "gemini",
        "gemini-3.1-flash-lite-preview"
    )

    assert len(response.macro_events) == 1
    assert response.macro_events[0].is_government_incentive is True
    assert response.macro_events[0].source_id == "gov_2"
