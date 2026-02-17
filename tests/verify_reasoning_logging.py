import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Mock problematic dependencies before imports
import unittest.mock
def mock_module(name):
    m = unittest.mock.MagicMock()
    sys.modules[name] = m
    return m

mock_module("anthropic")
mock_module("instructor")
mock_module("google.genai")
# Don't mock 'google' itself as it breaks 'google.protobuf'

# Mock internal submodules to avoid triggering their imports in core.llm.__init__
mock_module("core.llm.analysis")
mock_module("core.llm.events")
mock_module("core.llm.clients")
mock_module("core.llm.tools")

# Add apps/engine to sys.path
engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/engine"))
sys.path.append(engine_path)

from core.llm.logger import log_reasoning_trace

async def test_log_reasoning_trace():
    print("Running test_log_reasoning_trace...")
    
    # Mock Supabase
    with patch("core.llm.logger.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        
        # Data
        task_type = "TEST_TASK"
        provider = "test_provider"
        model = "test_model"
        prompt = [{"role": "user", "content": "hello"}]
        response = {"answer": "hi"}
        metadata = {"ticker": "AAPL"}
        
        # Call
        await log_reasoning_trace(task_type, provider, model, prompt, response, metadata)
        
        # Verify
        mock_client.table.assert_called_once_with("llm_reasoning_logs")
        mock_table.insert.assert_called_once()
        args, _ = mock_table.insert.call_args
        payload = args[0]
        
        assert payload["task_type"] == task_type
        assert payload["model_provider"] == provider
        assert payload["model_name"] == model
        assert payload["prompt"] == prompt
        assert payload["response"] == response
        assert payload["metadata"] == metadata
        assert "created_at" in payload
        
        print("Basic logging test passed!")

async def test_gemini_object_handling():
    print("Running test_gemini_object_handling...")
    
    # Simple mock for Gemini Content/Part objects
    class MockPart:
        def __init__(self, text=None, function_call=None):
            self.text = text
            self.function_call = function_call
            self.function_response = None
            self.thought = None

    class MockContent:
        def __init__(self, role, parts):
            self.role = role
            self.parts = parts

    with patch("core.llm.logger.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        
        mock_fc = MagicMock()
        mock_fc.name = "get_quote"
        mock_fc.args = {"ticker": "AAPL"}
        
        prompt = [
            MockContent(role="user", parts=[MockPart(text="price of AAPL?")]),
            MockContent(role="model", parts=[MockPart(function_call=mock_fc)])
        ]
        
        await log_reasoning_trace("INGESTION", "gemini", "gemini-1.5-pro", prompt, {"status": "ok"})
        
        args, _ = mock_table.insert.call_args
        payload = args[0]
        
        assert len(payload["prompt"]) == 2
        assert payload["prompt"][0]["role"] == "user"
        assert payload["prompt"][0]["parts"][0]["text"] == "price of AAPL?"
        assert payload["prompt"][1]["role"] == "model"
        assert payload["prompt"][1]["parts"][0]["function_call"]["name"] == "get_quote"
        
        print("Gemini object handling test passed!")

if __name__ == "__main__":
    asyncio.run(test_log_reasoning_trace())
    asyncio.run(test_gemini_object_handling())
