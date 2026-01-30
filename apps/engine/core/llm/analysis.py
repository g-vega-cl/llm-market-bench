"""Core LLM analysis logic for trading decisions."""

import asyncio
import json
import logging

from core.models import DecisionsResponse
from core.llm import clients
from core.llm import prompts
from core.llm import tools

logger = logging.getLogger("engine")


async def analyze_with_provider(
    provider: str,
    model_name: str,
    chunks: list[dict],
    context: str = "",
    portfolio_context: str = "",
) -> DecisionsResponse:
    """Analyzes a batch of newsletter chunks using the specified provider.

    Args:
        provider: The LLM provider name (openai, anthropic, gemini, deepseek).
        model_name: The specific model identifier for the provider.
        chunks: List of dictionaries containing 'source_id' and 'content'.
        context: Aggregated historical context.
        portfolio_context: Current portfolio status context.

    Returns:
        A DecisionsResponse instance containing trading signals and macro events.

    Raises:
        ValueError: If the provider is not recognized.
        Exception: If the LLM API call fails after retries.
    """
    factory = clients.CLIENT_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(f"Unknown provider: {provider}")

    client = factory()

    try:
        # Construct batch prompt
        news_content = ""
        for chunk in chunks:
            news_content += (
                f"\n---\nSource ID: {chunk['source_id']}\n"
                f"Content: {chunk['content']}\n---\n"
            )

        prompt = prompts.ANALYSIS_USER_PROMPT_TEMPLATE.format(
            portfolio_context=portfolio_context if portfolio_context else "No portfolio data available.",
            context=context if context else "No relevant historical context found.",
            news_content=news_content,
        )

        messages = [
            {
                "role": "system",
                "content": prompts.ANALYSIS_SYSTEM_PROMPT,
            },
            {"role": "user", "content": prompt},
        ]

        # Tool execution loop
        max_tool_steps = 5
        for _ in range(max_tool_steps):
            args = {
                "model": model_name,
                "messages": messages,
            }

            # Add provider-specific tool definitions
            if provider == "openai":
                args["tools"] = [
                    tools.STOCK_TOOL_DEFINITION_OPENAI,
                    tools.PRICE_HISTORY_TOOL_DEFINITION_OPENAI,
                    tools.POSITION_PNL_TOOL_DEFINITION_OPENAI,
                ]
            elif provider == "anthropic":
                args["tools"] = [
                    tools.STOCK_TOOL_DEFINITION_ANTHROPIC,
                    tools.PRICE_HISTORY_TOOL_DEFINITION_ANTHROPIC,
                    tools.POSITION_PNL_TOOL_DEFINITION_ANTHROPIC,
                ]
                args["max_tokens"] = 8000
                # Anthropic requires system prompt separately
                if messages[0]["role"] == "system":
                    args["system"] = messages[0]["content"]
                    args["messages"] = messages[1:]
                args["messages"] = messages[1:]
            elif provider == "gemini":
                args["tools"] = [
                    tools.STOCK_TOOL_DEFINITION_GEMINI,
                    tools.PRICE_HISTORY_TOOL_DEFINITION_GEMINI,
                    tools.POSITION_PNL_TOOL_DEFINITION_GEMINI,
                ]
            elif provider == "deepseek":
                # DeepSeek-reasoner does not support manual tools well in this loop.
                # Skip manual tool loop and proceed directly to final structured extraction.
                break

            # Call the LLM (using the unwrapped client for intermediate steps if needed)
            raw_client = client.client

            if provider in ["openai", "deepseek"]:
                try:
                    resp = await raw_client.chat.completions.create(**args)
                except Exception as e:
                    logger.warning(f"Tool execution failed for {provider}/{model_name}, falling back to basic analysis: {e}")
                    break
                msg = resp.choices[0].message
                # Convert to dict for safety and persistence in next rounds
                messages.append(msg.model_dump())

                if not msg.tool_calls:
                    break

                for tool_call in msg.tool_calls:
                    call_args = json.loads(tool_call.function.arguments)
                    if tool_call.function.name == "get_stock_quote":
                        result = await tools.execute_stock_tool(call_args["ticker"])
                    elif tool_call.function.name == "get_price_history":
                        result = await tools.execute_price_history_tool(
                            call_args["ticker"], 
                            call_args.get("days", 7)
                        )
                    elif tool_call.function.name == "get_position_pnl":
                        result = await tools.execute_position_pnl_tool(
                            call_args["ticker"], 
                            owner_id=model_name
                        )
                    else:
                        continue

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })

            elif provider == "anthropic":
                try:
                    resp = await raw_client.messages.create(**args)
                except Exception as e:
                    logger.warning(f"Tool execution failed for {provider}/{model_name}, falling back to basic analysis: {e}")
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
                    if tool_use.name == "get_stock_quote":
                        result = await tools.execute_stock_tool(tool_use.input["ticker"])
                    elif tool_use.name == "get_price_history":
                        result = await tools.execute_price_history_tool(
                            tool_use.input["ticker"], 
                            tool_use.input.get("days", 7)
                        )
                    elif tool_use.name == "get_position_pnl":
                        result = await tools.execute_position_pnl_tool(
                            tool_use.input["ticker"], 
                            owner_id=model_name
                        )
                    else:
                        continue

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

            elif provider == "gemini":
                try:
                    # Using the google-genai SDK (raw_client is genai.Client)
                    # We need to convert OpenAI-style messages to Gemini contents (user/model roles)
                    contents = []
                    system_instruction = None
                    for m in messages:
                        if m["role"] == "system":
                            system_instruction = m["content"]
                            continue
                        
                        # Map assistant -> model
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
                                        # Gemini uses function_response
                                        parts.append({
                                            "function_response": {
                                                "name": part["tool_use_id"].split("-")[0], # Fallback name
                                                "response": {"result": part["content"]}
                                            }
                                        })
                        
                        # Handle tool calls/results in part of the message
                        if m.get("tool_calls"):
                            for tc in m["tool_calls"]:
                                parts.append({
                                    "function_call": {
                                        "name": tc["function"]["name"],
                                        "args": json.loads(tc["function"]["arguments"])
                                    }
                                })
                        
                        if m["role"] == "tool":
                            # Map tool result back to user role with function_response
                            # We might need the name, which OpenAI format stores inside tool_call_id or we have to track it
                            # For simplicity, we'll try to find the matching name from our tool calls
                            # This is a bit complex in a loop, so we'll look for the last function_call in previous messages
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

                    # Call Gemini
                    resp = await raw_client.aio.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config={
                            "system_instruction": system_instruction,
                            "tools": [{"function_declarations": args["tools"]}]
                        }
                    )
                except Exception as e:
                    logger.warning(f"Tool execution failed for {provider}/{model_name}, falling back to basic analysis: {e}")
                    break
                
                # Process Gemini response
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
                
                if not model_message["tool_calls"]:
                    del model_message["tool_calls"]
                if not model_message["content"]:
                    del model_message["content"]
                
                messages.append(model_message)
                
                if not has_tool_call:
                    break
                
                # Execute Gemini tools
                for tc in model_message.get("tool_calls", []):
                    call_args = json.loads(tc["function"]["arguments"])
                    if tc["function"]["name"] == "get_stock_quote":
                        result = await tools.execute_stock_tool(call_args["ticker"])
                    elif tc["function"]["name"] == "get_price_history":
                        result = await tools.execute_price_history_tool(
                            call_args["ticker"], 
                            call_args.get("days", 7)
                        )
                    elif tc["function"]["name"] == "get_position_pnl":
                        result = await tools.execute_position_pnl_tool(
                            call_args["ticker"], 
                            owner_id=model_name
                        )
                    else:
                        continue

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

        # Final structured extraction using Instructor
        logger.debug("Executing final extraction for %s/%s", provider, model_name)

        final_args = {
            "model": model_name,
            "response_model": DecisionsResponse,
            "messages": messages,
            "max_retries": 2,
        }

        if provider == "anthropic":
            final_args["max_tokens"] = 8000
            if messages[0]["role"] == "system":
                final_args["system"] = messages[0]["content"]
                final_args["messages"] = messages[1:]

        resp_awaitable = client.chat.completions.create(**final_args)

        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            final_resp = await resp_awaitable
        else:
            final_resp = resp_awaitable

        return final_resp

    except Exception as e:
        logger.error("Error analyzing batch with %s/%s: %s", provider, model_name, e)
        raise
    finally:
        # Ensure client is properly closed
        await clients.close_client(client, provider)
