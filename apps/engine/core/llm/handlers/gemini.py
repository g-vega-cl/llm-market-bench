"""Gemini tool loop handler."""

import inspect
import json
import logging

from google.genai import types

from core.llm import tools
from core.llm.handlers import base

logger = logging.getLogger("engine")

DEFAULT_GEMINI_TOOLS = [
    tools.to_gemini(t)
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
        tools.FETCH_DAILY_NEWSLETTER_TOOL,
        tools.FETCH_NEWSLETTER_CONTENT_TOOL,
        tools.SEARCH_PAST_MEMORIES_TOOL,
        tools.GET_OPTIONS_SENTIMENT_TOOL,
        tools.GET_OPTION_CHAIN_TOOL,
        tools.GET_TICKER_NEWS_TOOL,
        tools.GET_CONGRESS_TRADES_TOOL,
        tools.GET_INSIDER_TRADES_TOOL,
        tools.GET_WHALE_HOLDINGS_TOOL,
    )
]


def _generate_content_config_supports(field_name: str) -> bool:
    """Checks whether the local Gemini SDK supports a GenerateContentConfig field."""
    config_cls = types.GenerateContentConfig

    for attr_name in ("model_fields", "__annotations__", "__dataclass_fields__"):
        fields = getattr(config_cls, attr_name, None)
        if fields and field_name in fields:
            return True

    try:
        return field_name in inspect.signature(config_cls).parameters
    except (TypeError, ValueError):
        return False


def _build_gemini_tools(function_tools: list | None = None, enable_google_search: bool = False) -> list:
    """Builds the tool list for Gemini API.

    Args:
        function_tools: Optional list of function tool definitions.
            Defaults to DEFAULT_GEMINI_TOOLS.
        enable_google_search: Whether to include Google Search grounding.

    Returns:
        List of tool definitions.
    """
    if function_tools is None:
        function_tools = DEFAULT_GEMINI_TOOLS.copy()

    # Build the tools list with proper Gemini types
    gemini_tools = []

    # Add function declarations
    if function_tools:
        gemini_tools.append(types.Tool(function_declarations=function_tools))

    # Gemini can use Google Search grounding alongside function declarations.
    if enable_google_search:
        gemini_tools.append(types.Tool(google_search={}))

    return gemini_tools


def _resolve_tool_name_from_history(messages: list, tool_call_id: str) -> str:
    """Finds the function name corresponding to a tool_call_id in message history."""
    for prev in reversed(messages):
        if isinstance(prev, dict) and prev.get("tool_calls"):
            for ptc in prev["tool_calls"]:
                if ptc["id"] == tool_call_id:
                    return ptc["function"]["name"]
    return "unknown"


def _convert_dict_message_parts(m: dict, messages: list) -> tuple[str, list]:
    """Converts a single dict message into (role, parts) for Gemini API."""
    role = "model" if m["role"] in ["assistant", "model"] else "user"
    parts = []

    content = m.get("content")
    if content:
        if isinstance(content, str):
            parts.append({"text": content})
        elif isinstance(content, list):
            for part in content:
                if part.get("type") == "text":
                    parts.append({"text": part["text"]})
                elif part.get("type") == "tool_result":
                    parts.append(
                        {
                            "function_response": {
                                "name": part["tool_use_id"].split("-")[0],
                                "response": {"result": part["content"]},
                            }
                        }
                    )

    if m.get("tool_calls"):
        for tc in m["tool_calls"]:
            part = {
                "function_call": {
                    "name": tc["function"]["name"],
                    "args": json.loads(tc["function"]["arguments"]),
                }
            }
            if "thought" in tc:
                part["thought"] = tc["thought"]
            if "thought_signature" in tc:
                part["thought_signature"] = tc["thought_signature"]
            parts.append(part)

    if m["role"] == "tool":
        tool_name = _resolve_tool_name_from_history(messages, m["tool_call_id"])
        parts.append({"function_response": {"name": tool_name, "response": {"result": m["content"]}}})
        role = "user"

    return role, parts


def _build_gemini_contents(messages: list) -> tuple[list, str | None]:
    """Converts message history into Gemini contents list and system_instruction."""
    contents = []
    system_instruction = None
    for m in messages:
        if isinstance(m, types.Content):
            contents.append(m)
            continue

        if isinstance(m, dict) and m["role"] == "system":
            system_instruction = m["content"]
            continue

        role, parts = _convert_dict_message_parts(m, messages)
        if parts:
            contents.append({"role": role, "parts": parts})

    return contents, system_instruction


def _build_generate_content_config(
    system_instruction: str | None,
    tool_defs: list,
    enable_google_search: bool,
    thinking_level: str,
) -> types.GenerateContentConfig:
    """Constructs the GenerateContentConfig for a Gemini tool loop iteration."""
    gemini_tools = _build_gemini_tools(tool_defs, enable_google_search)

    config_kwargs = {
        "system_instruction": system_instruction,
        "tools": gemini_tools,
        "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        "safety_settings": [
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="BLOCK_NONE"),
        ],
    }
    if hasattr(types, "ThinkingConfig"):
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)

    if enable_google_search:
        sdk_supports_tool_config = (
            _generate_content_config_supports("tool_config")
            and hasattr(types, "ToolConfig")
            and "include_server_side_tool_invocations" in types.ToolConfig.model_fields
        )
        if sdk_supports_tool_config:
            config_kwargs["tool_config"] = types.ToolConfig(include_server_side_tool_invocations=True)

    return types.GenerateContentConfig(**config_kwargs)


async def _execute_gemini_tool_calls(tool_calls: list[dict], model_name: str) -> list[types.Part]:
    """Executes extracted Gemini function calls and returns FunctionResponse parts."""
    response_parts = []
    for tc in tool_calls:
        result = await base.execute_tool(tc["name"], tc["args"], model_name)
        fr_kwargs = {
            "name": tc["name"],
            "response": {"result": result},
        }
        if tc.get("id") and isinstance(tc["id"], str) and "id" in types.FunctionResponse.__annotations__:
            fr_kwargs["id"] = tc["id"]

        response_parts.append(types.Part(function_response=types.FunctionResponse(**fr_kwargs)))
    return response_parts


async def run_tool_loop(
    raw_client,
    model_name: str,
    messages: list,
    max_tool_steps: int = 5,
    override_tools: list | None = None,
    enable_google_search: bool = False,
    thinking_level: str = "high",
) -> None:
    """Runs the tool execution loop for Gemini.

    Args:
        raw_client: The underlying async Gemini client.
        model_name: The model identifier.
        messages: The message history (modified in-place).
        max_tool_steps: Maximum iterations.
        override_tools: Optional list of canonical (OpenAI-format) tool defs
            to override defaults. Translated to Gemini format internally.
        enable_google_search: Whether to enable Google Search grounding.
        thinking_level: Thinking depth level ('minimal', 'low', 'medium', 'high').
    """
    tool_defs = [tools.to_gemini(t) for t in override_tools] if override_tools is not None else DEFAULT_GEMINI_TOOLS

    for _ in range(max_tool_steps):
        contents, system_instruction = _build_gemini_contents(messages)

        try:
            config = _build_generate_content_config(system_instruction, tool_defs, enable_google_search, thinking_level)
            resp = await raw_client.aio.models.generate_content(model=model_name, contents=contents, config=config)
        except Exception as e:
            logger.warning(f"Tool execution failed for gemini/{model_name}, falling back to basic analysis: {e}")
            break
        if not resp.candidates or not resp.candidates[0].content:
            break

        candidate = resp.candidates[0]
        messages.append(candidate.content)

        tool_calls = [
            {
                "name": part.function_call.name,
                "args": part.function_call.args,
                "id": getattr(part.function_call, "id", None),
            }
            for part in candidate.content.parts
            if part.function_call
        ]

        if not tool_calls:
            break

        response_parts = await _execute_gemini_tool_calls(tool_calls, model_name)
        messages.append(types.Content(role="user", parts=response_parts))
