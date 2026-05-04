"""Mocked tests for the LLM tool-calling loop and format adapters."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from core.llm import analyze_with_provider
from core.models import DecisionsResponse, DecisionObject


# =============================================================================
# Format adapter unit tests (canonical → provider-specific)
# =============================================================================

def test_to_anthropic_translates_canonical():
    from core.llm.tools import to_anthropic
    canonical = {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "Get stock price",
            "parameters": {"type": "object", "properties": {}},
        },
    }
    result = to_anthropic(canonical)
    assert result["name"] == "get_stock_quote"
    assert result["description"] == "Get stock price"
    assert result["input_schema"] == {"type": "object", "properties": {}}
    assert "function" not in result
    assert "type" not in result


def test_to_gemini_translates_canonical():
    from core.llm.tools import to_gemini
    canonical = {
        "type": "function",
        "function": {
            "name": "calculate_buy_quantity",
            "description": "desc",
            "parameters": {"type": "object", "required": ["percentage"]},
        },
    }
    result = to_gemini(canonical)
    assert result["name"] == "calculate_buy_quantity"
    assert result["description"] == "desc"
    assert result["parameters"] == {"type": "object", "required": ["percentage"]}
    assert "function" not in result
    assert "type" not in result


def test_to_gemini_strips_minimum_maximum():
    """minimum/maximum are stripped for backward compat with Gemini old defs."""
    from core.llm.tools import to_gemini
    canonical = {
        "type": "function",
        "function": {
            "name": "calculate_buy_quantity",
            "description": "desc",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "percentage": {
                        "type": "integer",
                        "description": "1-100",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["ticker", "percentage"],
            },
        },
    }
    result = to_gemini(canonical)
    perc = result["parameters"]["properties"]["percentage"]
    assert "minimum" not in perc
    assert "maximum" not in perc
    assert perc["type"] == "integer"
    assert perc["description"] == "1-100"


def test_to_gemini_preserves_parameters_without_properties():
    """Parameters dict without 'properties' key is passed through unmodified."""
    from core.llm.tools import to_gemini
    canonical = {
        "type": "function",
        "function": {
            "name": "foo",
            "description": "desc",
            "parameters": {"type": "object"},
        },
    }
    result = to_gemini(canonical)
    assert result["parameters"] == {"type": "object"}


# =============================================================================
# Format adapter validation tests
# =============================================================================

def test_to_anthropic_raises_on_missing_function_key():
    from core.llm.tools import to_anthropic
    with pytest.raises(KeyError, match="missing 'function' key"):
        to_anthropic({"type": "web_search"})


def test_to_anthropic_raises_on_function_not_dict():
    from core.llm.tools import to_anthropic
    with pytest.raises(TypeError, match="must be a dict"):
        to_anthropic({"function": "not_a_dict"})


def test_to_anthropic_raises_on_missing_required_subkeys():
    from core.llm.tools import to_anthropic
    with pytest.raises(KeyError, match="missing required keys"):
        to_anthropic({"function": {"name": "foo"}})


def test_to_gemini_raises_on_missing_function_key():
    from core.llm.tools import to_gemini
    with pytest.raises(KeyError, match="missing 'function' key"):
        to_gemini({"type": "web_search"})


def test_to_gemini_raises_on_malformed_function():
    from core.llm.tools import to_gemini
    with pytest.raises(TypeError, match="must be a dict"):
        to_gemini({"function": "not_a_dict"})


# =============================================================================
# Tool loop — override_tools edge cases
# =============================================================================

@pytest.mark.asyncio
async def test_openai_override_tools_empty_list_means_no_tools():
    """override_tools=[] should send an empty tools list, not default tools."""
    from core.llm.handlers import openai as openai_handler

    mock_exit_msg = MagicMock(tool_calls=None)
    mock_exit_msg.model_dump.return_value = {"role": "assistant", "content": "Done."}

    mock_raw_client = MagicMock()
    mock_raw_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[MagicMock(message=mock_exit_msg)])
    )

    messages = [{"role": "user", "content": "hi"}]
    await openai_handler.run_tool_loop(
        raw_client=mock_raw_client,
        model_name="gpt-4",
        messages=messages,
        override_tools=[],
    )

    call_kwargs = mock_raw_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["tools"] == []


@pytest.mark.asyncio
async def test_deepseek_override_tools_empty_list_means_no_tools():
    """override_tools=[] should send an empty tools list for deepseek too."""
    from core.llm.handlers import deepseek as deepseek_handler

    mock_exit_msg = MagicMock(tool_calls=None)
    mock_exit_msg.model_dump.return_value = {"role": "assistant", "content": "Done."}

    mock_raw_client = MagicMock()
    mock_raw_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[MagicMock(message=mock_exit_msg)])
    )

    messages = [{"role": "user", "content": "hi"}]
    await deepseek_handler.run_tool_loop(
        raw_client=mock_raw_client,
        model_name="deepseek-v4-pro",
        messages=messages,
        override_tools=[],
    )

    call_kwargs = mock_raw_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["tools"] == []


# =============================================================================
# Tool loop — full integration test
# =============================================================================

@pytest.mark.asyncio
async def test_analyze_with_provider_tool_loop():
    """Test that analyze_with_provider handles a tool call loop."""
    
    # Mock data
    mock_chunks = [{"source_id": "src_1", "content": "Buy Apple stock"}]
    
    # 1. Mock the raw OpenAI-style response for the first call (Tool Use)
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "get_stock_quote"
    mock_tool_call.function.arguments = json.dumps({"ticker": "AAPL"})
    
    mock_msg_with_tool = MagicMock()
    mock_msg_with_tool.role = "assistant"
    mock_msg_with_tool.tool_calls = [mock_tool_call]
    mock_msg_with_tool.content = None
    mock_msg_with_tool.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "get_stock_quote", "arguments": '{"ticker": "AAPL"}'}
            }
        ]
    }
    
    mock_openai_resp_1 = MagicMock()
    mock_openai_resp_1.choices = [MagicMock(message=mock_msg_with_tool)]
    
    # 2. Mock the final response (Structured Output via Instructor)
    mock_final_decision = DecisionsResponse(
        decisions=[
            DecisionObject(
                signal="BUY",
                confidence=90,
                reasoning="Verified price is reasonable.",
                ticker="AAPL",
                source_id="src_1",
                price=150.0
            )
        ]
    )
    
    with patch("core.llm.tools.MarketDataManager") as mock_manager_cls, \
         patch("core.llm.analysis.clients.CLIENT_FACTORIES") as mock_factories:
        
        # Mock MarketDataManager
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(return_value=MagicMock(ticker="AAPL", price=150.0, market_cap=2.5e12, exists=True))
        
        # Mock Client
        mock_client = MagicMock()
        mock_factories.get.return_value = lambda: mock_client
        
        # Setup the sequence of responses
        # First call (unwrapped) -> returns tool call
        # Second call (unwrapped) -> returns no tool call
        # Final call (wrapped via instructor) -> returns structured response
        
        # For simplicity, we'll mock chat.completions.create on both the mock_client (wrapped) 
        # and mock_client.client (unwrapped)
        
        # Mock unwrapped client tool loop
        mock_raw_client = mock_client.client
        
        # Configure return values for tool-calling loop
        # The tool loop expects objects from the raw client
        mock_exit_msg = MagicMock(tool_calls=None)
        mock_exit_msg.model_dump.return_value = {"role": "assistant", "content": "Done."}
        
        mock_raw_client.chat.completions.create = AsyncMock(side_effect=[
            mock_openai_resp_1,
            MagicMock(choices=[MagicMock(message=mock_exit_msg)])
        ])
        
        # Mock wrapped instructor extraction
        mock_client.chat.completions.create = AsyncMock(return_value=[mock_final_decision])
        
        # Execute
        result = await analyze_with_provider("openai", "gpt-4", mock_chunks)
        
        # Assertions
        assert len(result.decisions) == 1
        assert result.decisions[0].ticker == "AAPL"
        assert mock_manager.get_quote.call_count == 1
        # The loop iterates twice: once for the tool call, once to break on no tool call
        assert mock_raw_client.chat.completions.create.call_count == 2
