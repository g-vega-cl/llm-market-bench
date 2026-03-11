"""Tests for Hard Tool Enforcement in analysis.py."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.llm.analysis import analyze_with_provider, _scan_history_for_tools
from core.models import DecisionsResponse, DecisionObject

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
                    "function": {"name": "sell_50_percent", "arguments": '{"ticker": "AAPL"}'},
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
            MockPart("sell_100_percent", {"ticker": "GOOG"})
        ])
    ]
    
    res = _scan_history_for_tools(messages, "GOOG")
    assert res["quote_found"] is True
    assert res["sell_tool_found"] is True

@pytest.mark.asyncio
async def test_analyze_with_provider_hard_enforcement(mock_clients):
    """Verify that analyze_with_provider correctly updates sell_tool_called."""
    # Setup: Agent claims to have called sell tool but history is empty
    mock_instructor = mock_clients["instructor"]
    
    # DecisionsResponse returned by Instructor
    mock_instructor.create.return_value = DecisionsResponse(
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
    )
    
    # Mock handlers to not add any tools to messages
    with patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock):
        resp = await analyze_with_provider(
            provider="openai",
            model_name="gpt-4",
            chunks=[{"source_id": "s1", "content": "..."}]
        )
        
    # Verify that the final decision has sell_tool_called=False because history was empty
    assert resp.decisions[0].ticker == "AAPL"
    assert resp.decisions[0].sell_tool_called is False # UPDATED BY HARD ENFORCEMENT
