from unittest.mock import AsyncMock, MagicMock

import pytest

from core.llm.handlers import deepseek


@pytest.mark.asyncio
async def test_run_tool_loop_serialization():
    """Test that DeepSeek handler correctly serializes tool calls using model_dump."""

    mock_resp = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = "Let's check the price."
    mock_msg.reasoning_content = "<think>I need to check the price before buying.</think>"

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_abc123"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "get_stock_quote"
    mock_tool_call.function.arguments = '{"ticker": "AAPL"}'

    # Mock the behavior of model_dump returning a dictionary
    mock_tool_call.model_dump.return_value = {
        "id": "call_abc123",
        "type": "function",
        "function": {"name": "get_stock_quote", "arguments": '{"ticker": "AAPL"}'},
    }

    mock_msg.tool_calls = [mock_tool_call]
    mock_resp.choices = [MagicMock(message=mock_msg)]

    mock_client = MagicMock()
    # First call returns tool call, second call returns final text

    mock_resp2 = MagicMock()
    mock_msg2 = MagicMock()
    mock_msg2.content = "I've checked the price."
    mock_msg2.reasoning_content = "<think>Price is fine.</think>"
    mock_msg2.tool_calls = None
    mock_resp2.choices = [MagicMock(message=mock_msg2)]

    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_resp, mock_resp2])

    messages = [{"role": "user", "content": "Analyze AAPL"}]

    # Mock base.execute_tool so it doesn't fail
    with pytest.MonkeyPatch.context() as m:
        m.setattr("core.llm.handlers.base.execute_tool", AsyncMock(return_value="Current Price: $150"))

        # Run loop
        await deepseek.run_tool_loop(
            raw_client=mock_client,
            model_name="deepseek-v4-pro",
            messages=messages,
            provider="deepseek",
            max_tool_steps=2,
        )

    # Validate the tool call serialization in the messages list
    assistant_msg = next(
        (m for m in messages if m["role"] == "assistant" and "tool_calls" in m and m["tool_calls"]), None
    )

    assert assistant_msg is not None, "Assistant message with tool calls not found in history"
    assert assistant_msg["reasoning_content"] == "<think>I need to check the price before buying.</think>"
    assert isinstance(assistant_msg["tool_calls"], list)
    assert isinstance(assistant_msg["tool_calls"][0], dict), "Tool call was not serialized into a dictionary!"
    assert assistant_msg["tool_calls"][0]["id"] == "call_abc123"
