"""DeepSeek-specific tool loop handler."""

import json
import logging

from core.llm.handlers import base
from core.llm.handlers.openai import _build_tool_list

logger = logging.getLogger("engine")


async def run_tool_loop(
    raw_client,
    model_name: str,
    messages: list,
    provider: str = "deepseek",
    max_tool_steps: int = 5,
    override_tools: list | None = None,
    enable_web_search: bool = False,
) -> None:
    """Runs the tool execution loop for DeepSeek.

    Args:
        raw_client: The underlying async OpenAI client.
        model_name: The model identifier.
        messages: The message history (modified in-place).
        provider: The provider name (default deepseek).
        max_tool_steps: Maximum iterations.
        override_tools: Optional list of tools to override defaults.
        enable_web_search: Whether to enable native web search tool.
    """
    import typing

    for _ in range(max_tool_steps):
        args: dict[str, typing.Any] = {
            "model": model_name,
            "messages": messages,
            "tools": override_tools if override_tools is not None else _build_tool_list(enable_web_search),
        }

        # DeepSeek specific: Enable thinking mode (all v4 models support it)
        if "deepseek" in model_name.lower():
            args["extra_body"] = {"thinking": {"type": "enabled"}}

            # DeepSeek requires reasoning_content to be present if tool_calls is present.
            # We clear it for messages WITHOUT tool calls to save context window.
            for msg in messages:
                if isinstance(msg, dict):
                    if msg.get("tool_calls"):
                        continue
                    if "reasoning_content" in msg:
                        msg["reasoning_content"] = None
                elif hasattr(msg, "reasoning_content"):
                    if getattr(msg, "tool_calls", None):
                        continue
                    msg.reasoning_content = None

        try:
            resp = await raw_client.chat.completions.create(**args)
        except Exception as e:
            logger.warning(f"Tool execution failed for {provider}/{model_name}, falling back to basic analysis: {e}")
            break

        msg = resp.choices[0].message

        # Append the raw response object or dict correctly preserving reasoning_content
        if hasattr(msg, "reasoning_content"):
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "reasoning_content": msg.reasoning_content,
                    "tool_calls": [tc.model_dump() for tc in msg.tool_calls]
                    if getattr(msg, "tool_calls", None)
                    else None,
                }
            )
        else:
            # model_dump() usually strips reasoning_content if it's not in the official OpenAI schema
            messages.append(msg.model_dump())

        if not msg.tool_calls:
            break

        for tool_call in msg.tool_calls:
            call_args = json.loads(tool_call.function.arguments)
            result = await base.execute_tool(tool_call.function.name, call_args, model_name)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )


def prepare_messages_for_instructor(messages: list) -> list:
    """Prepares DeepSeek messages for final Instructor extraction.

    DeepSeek with thinking mode returns reasoning_content but may leave content empty.
    This function ensures all messages are properly formatted for Instructor.

    Args:
        messages: The message history from the tool loop.

    Returns:
        Cleaned message list with reasoning_content cleared for non-tool-call messages.
    """
    cleaned = []
    for msg in messages:
        if isinstance(msg, dict):
            # Create a copy to avoid mutating original
            cleaned_msg = msg.copy()
            # Clear reasoning_content for messages without tool_calls
            if not cleaned_msg.get("tool_calls"):
                cleaned_msg["reasoning_content"] = None
            # Ensure content is not just whitespace
            if cleaned_msg.get("content") and cleaned_msg["content"].strip() == "":
                cleaned_msg["content"] = ""
            cleaned.append(cleaned_msg)
        else:
            # For non-dict messages, pass through
            cleaned.append(msg)
    return cleaned


def has_valid_content(messages: list) -> bool:
    """Checks if the last assistant message has valid (non-empty) content.

    Args:
        messages: The message history.

    Returns:
        True if the last assistant message has non-empty content.
    """
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content", "")
            return bool(content and content.strip())
    return False
