"""Tool Transcript Normalization Utility.

This module provides functions to transform raw provider tool calls into a
canonical schema (CanonicalTranscript) for consistent auditing and benchmark analysis.
"""

import json
from typing import Any, List, Dict
from core.models import CanonicalTranscript, CanonicalToolCall

def normalize_transcript(messages: List[Dict[str, Any]]) -> CanonicalTranscript:
    """Normalizes provider-specific message history into a canonical transcript.

    Args:
        messages: The raw message history from an LLM provider (OpenAI, Anthropic, Gemini, etc.).

    Returns:
        A CanonicalTranscript object containing normalized tool calls and messages.
    """
    normalized_calls = []

    # Iterate through messages to extract and normalize tool calls
    for i, msg in enumerate(messages):
        # 1. OpenAI / DeepSeek Format
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                # The result of the tool call is typically in the FOLLOWING message(s)
                # with role 'tool' and a matching tool_call_id.
                call_id = tc.get("id")
                tool_name = tc.get("function", {}).get("name")
                tool_args = tc.get("function", {}).get("arguments")
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except:
                        pass

                # Find matching result
                result = None
                for next_msg in messages[i+1:]:
                    if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") == call_id:
                        result = next_msg.get("content")
                        break

                normalized_calls.append(CanonicalToolCall(
                    id=call_id or "unknown",
                    name=tool_name or "unknown",
                    arguments=tool_args or {},
                    result=str(result) if result is not None else None,
                    raw_name=tool_name,
                    raw_arguments=str(tc.get("function", {}).get("arguments")),
                    raw_result=result,
                    provider_call_id=call_id
                ))

        # 2. Anthropic Format (content as list of blocks)
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_use":
                    call_id = block.get("id")
                    tool_name = block.get("name")
                    tool_args = block.get("input")

                    # Result is in a subsequent message with role 'user' and block type 'tool_result'
                    result = None
                    for next_msg in messages[i+1:]:
                        next_content = next_msg.get("content")
                        if next_msg.get("role") == "user" and isinstance(next_content, list):
                            for next_block in next_content:
                                if next_block.get("type") == "tool_result" and next_block.get("tool_use_id") == call_id:
                                    result = next_block.get("content")
                                    break
                        if result is not None:
                            break

                    normalized_calls.append(CanonicalToolCall(
                        id=call_id or "unknown",
                        name=tool_name or "unknown",
                        arguments=tool_args or {},
                        result=str(result) if result is not None else None,
                        raw_name=tool_name,
                        raw_arguments=str(tool_args),
                        raw_result=result,
                        provider_call_id=call_id
                    ))

        # 3. Gemini Format (parts)
        parts = msg.get("parts")
        if isinstance(parts, list):
            for part in parts:
                if part.get("function_call"):
                    fc = part["function_call"]
                    tool_name = fc.get("name")
                    tool_args = fc.get("args")

                    # Gemini doesn't always have a distinct ID like OpenAI/Anthropic
                    # But it uses tool_name linkage in function_response
                    result = None
                    for next_msg in messages[i+1:]:
                        next_parts = next_msg.get("parts")
                        if isinstance(next_parts, list):
                            for next_part in next_parts:
                                if next_part.get("function_response") and next_part["function_response"].get("name") == tool_name:
                                    result = next_part["function_response"].get("response")
                                    break
                        if result is not None:
                            break

                    normalized_calls.append(CanonicalToolCall(
                        id=tool_name, # Fallback to name as ID for Gemini
                        name=tool_name or "unknown",
                        arguments=tool_args or {},
                        result=str(result) if result is not None else None,
                        raw_name=tool_name,
                        raw_arguments=str(tool_args),
                        raw_result=result
                    ))

    return CanonicalTranscript(
        messages=messages,
        tool_calls=normalized_calls
    )
