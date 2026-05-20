"""OpenAI-compatible tool loop handler."""

import json
import logging

from core.llm import tools
from core.llm.handlers import base

logger = logging.getLogger("engine")

# Default function tools for OpenAI (canonical format is OpenAI-native).
DEFAULT_OPENAI_TOOLS = [
    tools.STOCK_TOOL,
    tools.PRICE_HISTORY_TOOL,
    tools.POSITION_PNL_TOOL,
    tools.CALCULATE_BUY_QUANTITY_TOOL,
    tools.CALCULATE_SELL_QUANTITY_TOOL,
    tools.FIND_UNCORRELATED_ASSETS_TOOL,
]

# OpenAI web search tool (native tool, not a function)
# Note: OpenAI web search requires search-enabled models in Chat Completions API:
# - gpt-5-search-api
# - gpt-4o-search-preview
# - gpt-4o-mini-search-preview
# Or use the Responses API with any supported model.
# See: https://developers.openai.com/api/docs/models/gpt-5
WEB_SEARCH_TOOL_OPENAI = {
    "type": "web_search",
    "name": "web_search",
}


def _build_tool_list(enable_web_search: bool = False) -> list:
    """Builds the tool list for OpenAI API.

    Args:
        enable_web_search: Whether to include web search tool.

    Returns:
        List of tool definitions.
    """
    if enable_web_search:
        return DEFAULT_OPENAI_TOOLS + [WEB_SEARCH_TOOL_OPENAI]
    return DEFAULT_OPENAI_TOOLS


async def run_tool_loop(
    raw_client,
    model_name: str,
    messages: list,
    provider: str = "openai",
    max_tool_steps: int = 5,
    override_tools: list | None = None,
    enable_web_search: bool = False,
) -> None:
    """Runs the tool execution loop for OpenAI.

    Args:
        raw_client: The underlying async OpenAI client.
        model_name: The model identifier.
        messages: The message history (modified in-place).
        provider: The provider name.
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

        try:
            resp = await raw_client.chat.completions.create(**args)
        except Exception as e:
            logger.warning(f"Tool execution failed for {provider}/{model_name}, falling back to basic analysis: {e}")
            break

        msg = resp.choices[0].message
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
