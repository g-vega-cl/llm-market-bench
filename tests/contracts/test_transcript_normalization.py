import pytest
from apps.engine.core.llm.normalization import normalize_transcript

def test_normalize_openai_transcript():
    """Ensures OpenAI-style transcripts are correctly normalized."""
    messages = [
        {"role": "user", "content": "What is AAPL price?"},
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "call_123", "function": {"name": "get_stock_quote", "arguments": '{"ticker": "AAPL"}'}}
            ]
        },
        {"role": "tool", "tool_call_id": "call_123", "content": "Price: 150.00"}
    ]

    transcript = normalize_transcript(messages)
    assert len(transcript.tool_calls) == 1
    call = transcript.tool_calls[0]
    assert call.id == "call_123"
    assert call.name == "get_stock_quote"
    assert call.arguments == {"ticker": "AAPL"}
    assert call.result == "Price: 150.00"

def test_normalize_anthropic_transcript():
    """Ensures Anthropic-style transcripts are correctly normalized."""
    messages = [
        {"role": "user", "content": "Check AAPL"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me check..."},
                {"type": "tool_use", "id": "tc_1", "name": "get_stock_quote", "input": {"ticker": "AAPL"}}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "tc_1", "content": "150.0"}
            ]
        }
    ]

    transcript = normalize_transcript(messages)
    assert len(transcript.tool_calls) == 1
    call = transcript.tool_calls[0]
    assert call.id == "tc_1"
    assert call.name == "get_stock_quote"
    assert call.result == "150.0"

def test_normalize_gemini_transcript():
    """Ensures Gemini-style transcripts are correctly normalized."""
    messages = [
        {"role": "user", "parts": [{"text": "Price for NVDA"}]},
        {
            "role": "model",
            "parts": [
                {"function_call": {"name": "get_stock_quote", "args": {"ticker": "NVDA"}}}
            ]
        },
        {
            "role": "user",
            "parts": [
                {"function_response": {"name": "get_stock_quote", "response": {"result": "800.0"}}}
            ]
        }
    ]

    transcript = normalize_transcript(messages)
    assert len(transcript.tool_calls) == 1
    call = transcript.tool_calls[0]
    assert call.name == "get_stock_quote"
    assert call.result == "{'result': '800.0'}" # Gemini mock normalization result
