"""Mocked tests for the LLM tool-calling loop."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from core.llm import analyze_with_provider
from core.models import DecisionsResponse, DecisionObject


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
    
    with patch("core.llm.MarketDataManager") as mock_manager_cls, \
         patch("core.llm._CLIENT_FACTORIES") as mock_factories:
        
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
        mock_client.chat.completions.create = AsyncMock(return_value=mock_final_decision)
        
        # Execute
        result = await analyze_with_provider("openai", "gpt-4", mock_chunks)
        
        # Assertions
        assert len(result.decisions) == 1
        assert result.decisions[0].ticker == "AAPL"
        assert mock_manager.get_quote.call_count == 1
        # The loop iterates twice: once for the tool call, once to break on no tool call
        assert mock_raw_client.chat.completions.create.call_count == 2
