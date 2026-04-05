import sys
import os
import json
from unittest.mock import MagicMock

# Add apps/engine to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.llm.analysis import _scan_history_for_tools

def test_history_scanner_with_objects():
    # Mock tool call object (OpenAI style)
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "get_stock_quote"
    mock_tool_call.function.arguments = json.dumps({"ticker": "AAPL"})
    
    # Message with tool call as object
    message_obj = MagicMock(spec=["tool_calls"])
    message_obj.tool_calls = [mock_tool_call]
    
    # Message with tool call as dict
    message_dict = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "1",
                "function": {
                    "name": "calculate_sell_quantity",
                    "arguments": json.dumps({"ticker": "AAPL", "percentage": 50})
                }
            }
        ]
    }
    
    history = [message_obj, message_dict]
    
    print(f"DEBUG: message_obj tool_calls: {message_obj.tool_calls}")
    print(f"DEBUG: first tool call name: {message_obj.tool_calls[0].function.name}")
    
    results = _scan_history_for_tools(history, "AAPL")
    
    print(f"Results: {results}")
    assert results["quote_found"] is True
    assert results["sell_tool_found"] is True
    print("Test Passed!")

if __name__ == "__main__":
    try:
        test_history_scanner_with_objects()
    except Exception as e:
        print(f"Test Failed: {e}")
        sys.exit(1)
