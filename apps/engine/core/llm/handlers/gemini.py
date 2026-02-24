"""Gemini tool loop handler."""

import json
import logging
from google.genai import types
from core.llm import tools
from core.llm.handlers import base

logger = logging.getLogger("engine")

async def run_tool_loop(
    raw_client, 
    model_name: str, 
    messages: list, 
    max_tool_steps: int = 5,
    override_tools: list | None = None
) -> None:
    """Runs the tool execution loop for Gemini."""
    tool_defs = override_tools or [
        tools.STOCK_TOOL_DEFINITION_GEMINI,
        tools.PRICE_HISTORY_TOOL_DEFINITION_GEMINI,
        tools.POSITION_PNL_TOOL_DEFINITION_GEMINI,
        tools.SELL_20_PERCENT_TOOL_DEFINITION_GEMINI,
        tools.SELL_50_PERCENT_TOOL_DEFINITION_GEMINI,
        tools.SELL_100_PERCENT_TOOL_DEFINITION_GEMINI,
    ]

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
            resp = await raw_client.aio.models.generate_content(
                model=model_name,
                contents=contents,
                config={
                    "system_instruction": system_instruction,
                    "tools": [{"function_declarations": tool_defs}]
                }
            )
        except Exception as e:
            logger.warning(f"Tool execution failed for gemini/{model_name}, falling back to basic analysis: {e}")
            break
        if not resp.candidates or not resp.candidates[0].content:
            break
        
        candidate = resp.candidates[0]
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
