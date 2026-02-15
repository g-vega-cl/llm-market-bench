import pytest
from unittest.mock import AsyncMock, MagicMock
from core.llm.handlers import anthropic

@pytest.mark.asyncio
async def test_run_tool_loop_strips_whitespace():
    # Mock Anthropic response with trailing whitespace in text block
    mock_resp = MagicMock()
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "I think we should buy AAPL.  "  # Trailing spaces
    mock_resp.content = [mock_text_block]
    
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_resp)
    
    messages = [{"role": "user", "content": "Analyze AAPL"}]
    
    # Run loop (should break after one iteration as no tool uses are present)
    await anthropic.run_tool_loop(
        raw_client=mock_client,
        model_name="claude-3-haiku",
        messages=messages,
        max_tool_steps=1
    )
    
    # Check if assistant message content has stripped whitespace
    assistant_msg = next(m for m in messages if m["role"] == "assistant")
    assert assistant_msg["content"][0]["text"] == "I think we should buy AAPL."
    assert not assistant_msg["content"][0]["text"].endswith(" ")
