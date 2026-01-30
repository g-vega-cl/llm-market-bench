"""Gemini tool loop handler."""

import json
import logging
from core.llm import tools
from core.llm.handlers import base

logger = logging.getLogger("engine")

async def run_tool_loop(
    raw_client, 
    model_name: str, 
    messages: list, 
    max_tool_steps: int = 5
) -> None:
    """Runs the tool execution loop for Gemini.

    Args:
        raw_client: The underlying async Google GenAI client.
        model_name: The model identifier.
        messages: The message history (modified in-place).
        max_tool_steps: Maximum iterations.
    """
    tool_defs = [
        tools.STOCK_TOOL_DEFINITION_GEMINI,
        tools.PRICE_HISTORY_TOOL_DEFINITION_GEMINI,
        tools.POSITION_PNL_TOOL_DEFINITION_GEMINI,
    ]

    for _ in range(max_tool_steps):
        # Convert OpenAI-style messages to Gemini contents
        contents = []
        system_instruction = None
        for m in messages:
            if m["role"] == "system":
                system_instruction = m["content"]
                continue
            
            role = "model" if m["role"] == "assistant" else "user"
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
                    parts.append({
                        "function_call": {
                            "name": tc["function"]["name"],
                            "args": json.loads(tc["function"]["arguments"])
                        }
                    })
            
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
        model_message = {"role": "assistant", "content": [], "tool_calls": []}
        has_tool_call = False
        
        for part in candidate.content.parts:
            if part.text:
                model_message["content"] = part.text
            if part.function_call:
                has_tool_call = True
                call_id = f"gemini-{part.function_call.name}-{len(messages)}"
                model_message["tool_calls"].append({
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": part.function_call.name,
                        "arguments": json.dumps(part.function_call.args)
                    }
                })
        
        if not model_message["tool_calls"]: del model_message["tool_calls"]
        if not model_message["content"]: del model_message["content"]
        
        messages.append(model_message)
        if not has_tool_call:
            break
        
        for tc in model_message.get("tool_calls", []):
            call_args = json.loads(tc["function"]["arguments"])
            result = await base.execute_tool(tc["function"]["name"], call_args, model_name)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })
