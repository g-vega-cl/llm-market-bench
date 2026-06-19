"""Anthropic tool loop handler."""

import logging

from core.config import (
    ANTHROPIC_MAX_WEB_SEARCHES,
    ANTHROPIC_WEB_SEARCH_VERSION,
    ENABLE_ANTHROPIC_WEB_SEARCH,
)
from core.llm import tools
from core.llm.handlers import base

logger = logging.getLogger("engine")

DEFAULT_ANTHROPIC_TOOLS = [
    tools.to_anthropic(t)
    for t in (
        tools.STOCK_TOOL,
        tools.PRICE_HISTORY_TOOL,
        tools.POSITION_PNL_TOOL,
        tools.CALCULATE_BUY_QUANTITY_TOOL,
        tools.CALCULATE_SELL_QUANTITY_TOOL,
        tools.FIND_UNCORRELATED_ASSETS_TOOL,
        tools.GET_KEY_METRICS_TOOL,
        tools.GET_MARKET_HEALTH_BAROMETER_TOOL,
        tools.GET_EARNINGS_HISTORY_TOOL,
        tools.SEARCH_PREDICTION_MARKETS_TOOL,
        tools.GET_PREDICTION_MARKET_ODDS_TOOL,
        tools.AUDIT_FINANCIAL_VALUATION_TOOL,
    )
]

# Anthropic web search tool with dynamic filtering (Opus 4.6 / Sonnet 4.6+).
# Not ZDR eligible by default.
WEB_SEARCH_TOOL_DYNAMIC_ANTHROPIC = {
    "type": "web_search_20260209",
    "name": "web_search",
}


def _get_web_search_tool():
    """Gets the web search tool definition based on config."""
    if ANTHROPIC_WEB_SEARCH_VERSION == "web_search_20260209":
        return WEB_SEARCH_TOOL_DYNAMIC_ANTHROPIC
    return {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": ANTHROPIC_MAX_WEB_SEARCHES,
    }


def _build_tool_list(enable_web_search: bool = False, override_tools: list | None = None) -> list:
    """Builds the tool list for Anthropic API.

    Translates canonical (OpenAI-format) tool defs from ``override_tools``
    if provided; otherwise uses ``DEFAULT_ANTHROPIC_TOOLS`` (already translated).

    Args:
        enable_web_search: Whether to include the Anthropic web search tool.
        override_tools: Optional list of canonical tool defs to use instead of defaults.

    Returns:
        List of Anthropic-format tool definitions.
    """
    if override_tools is not None:
        base_tools = [tools.to_anthropic(t) for t in override_tools]
    else:
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
    enable_web_search: bool = False,
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
            "max_tokens": 32000,  # Increased from 8000 to handle long tool execution loops
            "tools": _build_tool_list(enable_web_search, override_tools=override_tools),
        }
        if system_prompt:
            args["system"] = system_prompt

        try:
            resp = await raw_client.messages.create(**args)
        except Exception as e:
            logger.warning(f"Tool execution failed for anthropic/{model_name}, falling back to basic analysis: {e}")
            break

        # Check for function tool calls (client-side tools that we need to execute)
        tool_uses = [c for c in resp.content if c.type == "tool_use"]

        # Check for server tool calls (web_search - executed server-side by Anthropic)
        server_tool_uses = [c for c in resp.content if c.type == "server_tool_use"]

        # Log server tool usage for visibility (web searches performed)
        for server_tool in server_tool_uses:
            logger.info(f"Server tool executed by Anthropic: {server_tool.name}")

        # Build assistant message content
        # IMPORTANT: Do NOT include server_tool_use blocks in message history
        # Anthropic executes these server-side and they don't need tool_result blocks
        # Including them in history causes "tool_use without tool_result" errors
        assistant_content = []
        for content_block in resp.content:
            if content_block.type == "text":
                # Strip trailing whitespace to avoid "messages: final assistant content cannot end with trailing whitespace"
                text = content_block.text.rstrip() if content_block.text else ""
                if text:
                    assistant_content.append({"type": "text", "text": text})
            elif content_block.type == "tool_use":
                # Only include function tool calls (client-side tools)
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input,
                    }
                )
            # Skip server_tool_use blocks - they are internal to Anthropic's server

        # Ensure assistant content is never empty to avoid 400 errors from API
        if not assistant_content:
            assistant_content.append({"type": "text", "text": "Processing..."})

        messages.append({"role": "assistant", "content": assistant_content})

        # Only break if no function tool calls (server tools don't require our action)
        if not tool_uses:
            break

        # Collect tool results for function calls only
        tool_results_content = []

        # Handle function tool calls
        for tool_use in tool_uses:
            result = await base.execute_tool(tool_use.name, tool_use.input, model_name)
            tool_results_content.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                }
            )

        if tool_results_content:
            messages.append(
                {
                    "role": "user",
                    "content": tool_results_content,
                }
            )
