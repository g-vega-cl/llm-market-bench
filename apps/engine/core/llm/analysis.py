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
            if provider in ["openai", "deepseek"]:
                args["tools"] = [tools.STOCK_TOOL_DEFINITION_OPENAI]
            elif provider == "anthropic":
                args["tools"] = [tools.STOCK_TOOL_DEFINITION_ANTHROPIC]
                args["max_tokens"] = 8000
                # Anthropic requires system prompt separately
                if messages[0]["role"] == "system":
                    args["system"] = messages[0]["content"]
                    args["messages"] = messages[1:]
            elif provider == "gemini":
                # Instructor's GenAI wrapper handles tools via response_model best.
                # Skip manual tool loop and proceed directly to final structured extraction.
                break

            # Call the LLM (using the unwrapped client for intermediate steps if needed)
            raw_client = client.client

            if provider in ["openai", "deepseek"]:
                resp = await raw_client.chat.completions.create(**args)
                msg = resp.choices[0].message
                # Convert to dict for safety and persistence in next rounds
                messages.append(msg.model_dump())

                if not msg.tool_calls:
                    break

                for tool_call in msg.tool_calls:
                    if tool_call.function.name == "get_stock_quote":
                        call_args = json.loads(tool_call.function.arguments)
                        result = await tools.execute_stock_tool(call_args["ticker"])
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        })

            elif provider == "anthropic":
                resp = await raw_client.messages.create(**args)
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
