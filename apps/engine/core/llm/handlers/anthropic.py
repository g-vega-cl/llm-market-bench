"""Anthropic tool loop handler."""

import logging
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
    """Runs the tool execution loop for Anthropic.

    Args:
        raw_client: The underlying async Anthropic client.
        model_name: The model identifier.
        messages: The message history (modified in-place).
        max_tool_steps: Maximum iterations.
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
            "tools": override_tools or [
                tools.STOCK_TOOL_DEFINITION_ANTHROPIC,
                tools.PRICE_HISTORY_TOOL_DEFINITION_ANTHROPIC,
                tools.POSITION_PNL_TOOL_DEFINITION_ANTHROPIC,
            ]
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
                assistant_content.append({"type": "text", "text": content_block.text})
            elif content_block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": content_block.id,
                    "name": content_block.name,
                    "input": content_block.input,
                })

        messages.append({"role": "assistant", "content": assistant_content})

        tool_uses = [c for c in resp.content if c.type == "tool_use"]
        if not tool_uses:
            break

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
