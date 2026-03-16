import pytest
import dataclasses
from core.llm.logger import log_reasoning_trace
from unittest.mock import MagicMock, patch

@dataclasses.dataclass
class MockToolCall:
    name: str
    arguments: str

class MockMessage:
    def __init__(self, role, tool_calls=None):
        self.role = role
        self.tool_calls = tool_calls

@pytest.mark.asyncio
async def test_sterilization():
    # Setup mock data with non-serializable objects
    tool_call = MockToolCall(name="get_stock_quote", arguments='{"ticker": "NVDA"}')
    msg = MockMessage(role="assistant", tool_calls=[tool_call])
    
    prompt = [
        {"role": "user", "content": "Hello"},
        msg
    ]
    
    # Mock Supabase
    with patch("core.llm.logger.get_supabase_client") as mock_get_client:
        mock_table = MagicMock()
        mock_get_client.return_value.table.return_value = mock_table
        
        await log_reasoning_trace(
            task_type="TEST",
            model_provider="openai",
            model_name="gpt-4o",
            prompt=prompt,
            response={"status": "ok"}
        )
        
        # Verify the payload sent to execute()
        call_args = mock_table.insert.call_args[0][0]
        sent_prompt = call_args["prompt"]
        
        # Check that the second message was sterilized
        assert isinstance(sent_prompt[1], dict)
        assert sent_prompt[1]["role"] == "assistant"
        assert sent_prompt[1]["tool_calls"][0]["name"] == "get_stock_quote"
        assert isinstance(sent_prompt[1]["tool_calls"][0], dict)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_sterilization())
