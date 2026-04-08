"""Gemini tool loop handler."""

import json
import logging
import inspect
from google.genai import types
from google.genai import models as genai_models
from core.llm import tools
from core.llm.handlers import base

logger = logging.getLogger("engine")

# Default function tools for Gemini
DEFAULT_GEMINI_TOOLS = [
    tools.STOCK_TOOL_DEFINITION_GEMINI,
    tools.PRICE_HISTORY_TOOL_DEFINITION_GEMINI,
    tools.POSITION_PNL_TOOL_DEFINITION_GEMINI,
    tools.CALCULATE_BUY_QUANTITY_TOOL_DEFINITION_GEMINI,
    tools.CALCULATE_SELL_QUANTITY_TOOL_DEFINITION_GEMINI,
]

# Gemini Google Search grounding tool
GEMINI_GOOGLE_SEARCH_TOOL = tools.GEMINI_GOOGLE_SEARCH_TOOL


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


def _build_gemini_tools(
    function_tools: list | None = None,
    enable_google_search: bool = False
) -> list:
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


async def run_tool_loop(
    raw_client,
    model_name: str,
    messages: list,
    max_tool_steps: int = 5,
    override_tools: list | None = None,
    enable_google_search: bool = False
) -> None:
    """Runs the tool execution loop for Gemini.
    
    Args:
        raw_client: The underlying async Gemini client.
        model_name: The model identifier.
        messages: The message history (modified in-place).
        max_tool_steps: Maximum iterations.
        override_tools: Optional list of function tools to override defaults.
        enable_google_search: Whether to enable Google Search grounding.
    """
    tool_defs = override_tools or DEFAULT_GEMINI_TOOLS

    for _ in range(max_tool_steps):
        # Convert OpenAI-style messages or pass native Content
        contents = []
        system_instruction = None
        for m in messages:
            if isinstance(m, types.Content):
                contents.append(m)
                continue

            if isinstance(m, dict) and m["role"] == "system":
                system_instruction = m["content"]
                continue

            role = "model" if m["role"] in ["assistant", "model"] else "user"
            parts = []

            if m.get("content"):
                if isinstance(m["content"], str):
                    parts.append({"text": m["content"]})
                elif isinstance(m["content"], list):
                    for part in m["content"]:
                        if part.get("type") == "text":
                            parts.append({"text": part["text"]})
                        elif part.get("type") == "tool_result":
                            parts.append({
                                "function_response": {
                                    "name": part["tool_use_id"].split("-")[0],
                                    "response": {"result": part["content"]}
                                }
                            })

            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    part = {
                        "function_call": {
                            "name": tc["function"]["name"],
                            "args": json.loads(tc["function"]["arguments"])
                        }
                    }
                    if "thought" in tc:
                        part["thought"] = tc["thought"]
                    if "thought_signature" in tc:
                        part["thought_signature"] = tc["thought_signature"]
                    parts.append(part)

            if m["role"] == "tool":
                tool_name = "unknown"
                for prev in reversed(messages):
                    if prev.get("tool_calls"):
                        for ptc in prev["tool_calls"]:
                            if ptc["id"] == m["tool_call_id"]:
                                tool_name = ptc["function"]["name"]
                                break

                parts.append({
                    "function_response": {
                        "name": tool_name,
                        "response": {"result": m["content"]}
                    }
                })
                role = "user"

            if parts:
                contents.append({"role": role, "parts": parts})

        try:
            # Build tools list with Google Search if enabled
            gemini_tools = _build_gemini_tools(tool_defs, enable_google_search)
            
            config_kwargs = {
                "system_instruction": system_instruction,
                "tools": gemini_tools,
                "safety_settings": [
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="BLOCK_NONE"),
                ]
            }
            
            # Enable server-side tool invocations when using built-in tools (google_search)
            # with function declarations - required by Gemini API
            if enable_google_search:
                config_kwargs["tool_config"] = types.ToolConfig(
                    include_server_side_tool_invocations=True
                )
                # Disable AFC when using google_search with function declarations
                config_kwargs["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(
                    disable=True
                )
            
            config = types.GenerateContentConfig(**config_kwargs)
            
            resp = await raw_client.aio.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
        except Exception as e:
            logger.warning(f"Tool execution failed for gemini/{model_name}, falling back to basic analysis: {e}")
            break
        if not resp.candidates or not resp.candidates[0].content:
            break

        candidate = resp.candidates[0]
        
        # Check if this is a multi-function-call response (Gemini sometimes splits responses)
        # Count function calls in this response
        function_call_count = sum(1 for part in candidate.content.parts if part.function_call)
        
        # Append native Content object to history to preserve thought_signature
        messages.append(candidate.content)

        has_tool_call = False
        tool_calls = []
        for part in candidate.content.parts:
            if part.function_call:
                has_tool_call = True
                tool_calls.append({
                    "name": part.function_call.name,
                    "args": part.function_call.args
                })

        # If Gemini returned multiple function calls in one response, 
        # we need to execute all of them before breaking
        if not has_tool_call:
            break

        # Execute tools and append response as native Content
        response_parts = []
        for tc in tool_calls:
            result = await base.execute_tool(tc["name"], tc["args"], model_name)
            response_parts.append(
                types.Part.from_function_response(
                    name=tc["name"],
                    response={"result": result}
                )
            )

        messages.append(types.Content(role="user", parts=response_parts))
