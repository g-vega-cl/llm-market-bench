"""OpenAI-compatible tool loop handler."""

import json
import logging
from core.llm import tools
from core.llm.handlers import base

logger = logging.getLogger("engine")

async def run_tool_loop(
    raw_client, 
    model_name: str, 
    messages: list, 
    provider: str,
    max_tool_steps: int = 5,
    override_tools: list | None = None
) -> None:
    """Runs the tool execution loop for OpenAI/DeepSeek.

    Args:
        raw_client: The underlying async OpenAI client.
        model_name: The model identifier.
        messages: The message history (modified in-place).
        provider: The provider name.
        max_tool_steps: Maximum iterations.
    """
    for _ in range(max_tool_steps):
        args = {
            "model": model_name,
            "messages": messages,
            "tools": override_tools or [
                tools.STOCK_TOOL_DEFINITION_OPENAI,
                tools.PRICE_HISTORY_TOOL_DEFINITION_OPENAI,
                tools.POSITION_PNL_TOOL_DEFINITION_OPENAI,
                tools.SELL_10_PERCENT_TOOL_DEFINITION_OPENAI,
                tools.SELL_25_PERCENT_TOOL_DEFINITION_OPENAI,
                tools.SELL_33_PERCENT_TOOL_DEFINITION_OPENAI,
                tools.SELL_50_PERCENT_TOOL_DEFINITION_OPENAI,
                tools.SELL_75_PERCENT_TOOL_DEFINITION_OPENAI,
                tools.SELL_100_PERCENT_TOOL_DEFINITION_OPENAI,
            ]
        }
        
        if provider == "deepseek" and "reasoner" not in model_name:
            # Only breakout for deepseek-chat if needed, but deepseek-reasoner 
            # supports tools via the OpenAI SDK wrapper.
            # We'll allow reasoner to try the loop.
            pass

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
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
