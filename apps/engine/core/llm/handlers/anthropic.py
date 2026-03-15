"""Anthropic tool loop handler."""

import logging
from core.llm import tools
from core.llm.handlers import base
from core.config import (
    ENABLE_ANTHROPIC_WEB_SEARCH,
    ANTHROPIC_WEB_SEARCH_VERSION,
    ANTHROPIC_MAX_WEB_SEARCHES
)

logger = logging.getLogger("engine")

# Default tools for Anthropic (function tools)
DEFAULT_ANTHROPIC_TOOLS = [
    tools.STOCK_TOOL_DEFINITION_ANTHROPIC,
    tools.PRICE_HISTORY_TOOL_DEFINITION_ANTHROPIC,
    tools.POSITION_PNL_TOOL_DEFINITION_ANTHROPIC,
    tools.SELL_10_PERCENT_TOOL_DEFINITION_ANTHROPIC,
    tools.SELL_25_PERCENT_TOOL_DEFINITION_ANTHROPIC,
    tools.SELL_33_PERCENT_TOOL_DEFINITION_ANTHROPIC,
    tools.SELL_50_PERCENT_TOOL_DEFINITION_ANTHROPIC,
    tools.SELL_75_PERCENT_TOOL_DEFINITION_ANTHROPIC,
    tools.SELL_100_PERCENT_TOOL_DEFINITION_ANTHROPIC,
]


def _get_web_search_tool():
    """Gets the web search tool definition based on config."""
    if ANTHROPIC_WEB_SEARCH_VERSION == "web_search_20260209":
        return tools.WEB_SEARCH_TOOL_DYNAMIC_ANTHROPIC
    return {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": ANTHROPIC_MAX_WEB_SEARCHES,
    }


def _build_tool_list(enable_web_search: bool = False) -> list:
    """Builds the tool list for Anthropic API.
    
    Args:
        enable_web_search: Whether to include web search tool.
        
    Returns:
        List of tool definitions.
    """
    base_tools = DEFAULT_ANTHROPIC_TOOLS.copy()
    if enable_web_search and ENABLE_ANTHROPIC_WEB_SEARCH:
        base_tools.append(_get_web_search_tool())
    return base_tools


async def run_tool_loop(
    raw_client,
    model_name: str,
    messages: list,
    max_tool_steps: int = 5,
    override_tools: list | None = None,
    enable_web_search: bool = False
) -> None:
    """Runs the tool execution loop for Anthropic.

    Args:
        raw_client: The underlying async Anthropic client.
        model_name: The model identifier.
        messages: The message history (modified in-place).
        max_tool_steps: Maximum iterations.
        override_tools: Optional list of tools to override defaults.
        enable_web_search: Whether to enable native web search tool.
    """
    for _ in range(max_tool_steps):
        # Anthropic requires system prompt separately if present
        system_prompt = None
        current_messages = messages
        if messages[0]["role"] == "system":
            system_prompt = messages[0]["content"]
            current_messages = messages[1:]

        args = {
            "model": model_name,
            "messages": current_messages,
            "max_tokens": 8000,
            "tools": override_tools or _build_tool_list(enable_web_search),
        }
        if system_prompt:
            args["system"] = system_prompt

        try:
            resp = await raw_client.messages.create(**args)
        except Exception as e:
            logger.warning(f"Tool execution failed for anthropic/{model_name}, falling back to basic analysis: {e}")
            break

        # Append assistant response as a structured dict
        assistant_content = []
        for content_block in resp.content:
            if content_block.type == "text":
                # Strip trailing whitespace to avoid "messages: final assistant content cannot end with trailing whitespace"
                text = content_block.text.rstrip() if content_block.text else ""
                assistant_content.append({"type": "text", "text": text})
            elif content_block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": content_block.id,
                    "name": content_block.name,
                    "input": content_block.input,
                })
            elif content_block.type == "server_tool_use":
                # Native server tool (e.g., web_search)
                assistant_content.append({
                    "type": "server_tool_use",
                    "id": content_block.id,
                    "name": content_block.name,
                    "input": content_block.input,
                })

        messages.append({"role": "assistant", "content": assistant_content})

        # Check for function tool calls
        tool_uses = [c for c in resp.content if c.type == "tool_use"]
        
        # Check for server tool calls (web_search)
        server_tool_uses = [c for c in resp.content if c.type == "server_tool_use"]

        if not tool_uses and not server_tool_uses:
            break

        # Handle server tool results (web_search returns results directly in response)
        for server_tool in server_tool_uses:
            logger.info(f"Server tool invoked: {server_tool.name}")
            # Web search results are embedded in the response content blocks
            # We don't need to execute anything - Claude handles it natively
            # Just log for attribution

        # Handle function tool calls
        for tool_use in tool_uses:
            result = await base.execute_tool(tool_use.name, tool_use.input, model_name)

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    }
                ],
            })
