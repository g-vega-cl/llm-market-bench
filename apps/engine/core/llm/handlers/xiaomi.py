"""Xiaomi MiMo-specific tool loop handler."""

import json
import logging
from core.llm import tools
from core.llm.handlers import base
from core.llm.handlers.openai import _build_tool_list

logger = logging.getLogger("engine")

async def run_tool_loop(
    raw_client,
    model_name: str,
    messages: list,
    provider: str = "xiaomi",
    max_tool_steps: int = 5,
    override_tools: list | None = None,
    enable_web_search: bool = False
) -> None:
    """Runs the tool execution loop for Xiaomi MiMo.

    Args:
        raw_client: The underlying async OpenAI client.
        model_name: The model identifier.
        messages: The message history (modified in-place).
        provider: The provider name (default xiaomi).
        max_tool_steps: Maximum iterations.
        override_tools: Optional list of tools to override defaults.
        enable_web_search: Whether to enable native web search tool.
    """
    import typing
    for _ in range(max_tool_steps):
        args: typing.Dict[str, typing.Any] = {
            "model": model_name,
            "messages": messages,
            "tools": override_tools or _build_tool_list(enable_web_search),
        }

        # Xiaomi specific: Thinking mode is default for mimo-v2-pro
        # DeepSeek uses extra_body, but Xiaomi documentation doesn't mention it.
        # It says it returns reasoning_content alongside tool_calls.

        try:
            resp = await raw_client.chat.completions.create(**args)
        except Exception as e:
            logger.warning(f"Tool execution failed for {provider}/{model_name}, falling back to basic analysis: {e}")
            break

        msg = resp.choices[0].message

        # Xiaomi/MiMo specific: Content MUST not be an empty string. 
        # If it's empty, we use a placeholder or None. 
        # However, "None" (null) can also trigger "must contain at least one part" if no tool_calls are present.
        # We'll use a single space as a safe minimum if it's empty.
        assistant_msg = {
            "role": "assistant",
            "content": msg.content if msg.content and msg.content.strip() else " ",
            "tool_calls": getattr(msg, "tool_calls", None)
        }
        
        if hasattr(msg, "reasoning_content") and msg.reasoning_content:
            assistant_msg["reasoning_content"] = msg.reasoning_content
            
        messages.append(assistant_msg)

        if not msg.tool_calls:
            break

        for tool_call in msg.tool_calls:
            call_args = json.loads(tool_call.function.arguments)
            result = await base.execute_tool(tool_call.function.name, call_args, model_name)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })


def prepare_messages_for_instructor(messages: list) -> list:
    """Prepares Xiaomi messages for final Instructor extraction.
    
    Xiaomi with thinking mode returns reasoning_content but may leave content empty.
    This function ensures all messages are properly formatted for Instructor.
    
    Args:
        messages: The message history from the tool loop.
        
    Returns:
        Cleaned message list with reasoning_content preserved for tool-call messages.
    """
    cleaned = []
    for msg in messages:
        if isinstance(msg, dict):
            # Create a copy to avoid mutating original
            cleaned_msg = msg.copy()
            # Xiaomi/Instructor specific: 
            # We ensure content is a non-empty space if empty to avoid 400 errors.
            if "content" in cleaned_msg and (not cleaned_msg["content"] or not str(cleaned_msg["content"]).strip()):
                 cleaned_msg["content"] = " "
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
