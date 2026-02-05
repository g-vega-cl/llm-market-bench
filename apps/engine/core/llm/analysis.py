"""Core LLM analysis logic for trading decisions."""

import asyncio
import json
import logging

from core.models import DecisionsResponse
from core.llm import clients
from core.llm import prompts
from core.llm import tools
from core.config import MIN_TRADE_VALUE

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
        news_content = "".join([
            f"\n---\nSource ID: {chunk['source_id']}\nContent: {chunk['content']}\n---\n"
            for chunk in chunks
        ])

        prompt = prompts.ANALYSIS_USER_PROMPT_TEMPLATE.format(
            portfolio_context=portfolio_context if portfolio_context else "No portfolio data available.",
            context=context if context else "No relevant historical context found.",
            news_content=news_content,
            min_trade_value=MIN_TRADE_VALUE,
        )

        messages = [
            {"role": "system", "content": prompts.ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        # Tool execution loop (delegated to provider-specific handlers)
        raw_client = client.client
        if provider in ["openai", "deepseek"]:
            from core.llm.handlers import openai
            await openai.run_tool_loop(raw_client, model_name, messages, provider)
        elif provider == "anthropic":
            from core.llm.handlers import anthropic
            await anthropic.run_tool_loop(raw_client, model_name, messages)
        elif provider == "gemini":
            from core.llm.handlers import gemini
            await gemini.run_tool_loop(raw_client, model_name, messages)

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
        await clients.close_client(client, provider)
