"""Multi-provider LLM client factories and analysis functions.

This module provides a unified interface for interacting with multiple LLM
providers (OpenAI, Anthropic, Google Gemini, DeepSeek) using the Instructor
library for structured output validation.
"""

import asyncio
import logging

import instructor
from anthropic import AsyncAnthropic
from google import genai
from openai import AsyncOpenAI

from . import config
from .models import DecisionObject

logger = logging.getLogger("engine")


# --- Client Factories ---

def get_openai_client():
    """Creates an async OpenAI client wrapped with Instructor."""
    return instructor.from_openai(AsyncOpenAI(
        api_key=config.OPENAI_API_KEY,
        timeout=60.0
    ))


def get_anthropic_client():
    """Creates an async Anthropic client wrapped with Instructor."""
    return instructor.from_anthropic(AsyncAnthropic(
        api_key=config.ANTHROPIC_API_KEY,
        timeout=60.0
    ))


def get_deepseek_client():
    """Creates an async DeepSeek client (uses OpenAI SDK) wrapped with Instructor."""
    return instructor.from_openai(
        AsyncOpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            timeout=60.0
        ),
        mode=instructor.Mode.JSON
    )


def get_gemini_client():
    """Creates a Google Gemini client wrapped with Instructor."""
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    return instructor.from_genai(client)


# --- Provider Registry ---

_CLIENT_FACTORIES = {
    "openai": get_openai_client,
    "anthropic": get_anthropic_client,
    "deepseek": get_deepseek_client,
    "gemini": get_gemini_client,
}


# --- Analysis Functions ---

async def analyze_with_provider(
    provider: str,
    model_name: str,
    chunks: list[dict],
    context: str = ""
) -> list[DecisionObject]:
    """Analyzes a batch of newsletter chunks using the specified provider.

    Args:
        provider: The LLM provider name (openai, anthropic, gemini, deepseek).
        model_name: The specific model identifier for the provider.
        chunks: List of dictionaries containing 'source_id' and 'content'.
        context: Aggregated historical context.

    Returns:
        A list of DecisionObject instances giving trading signals.

    Raises:
        ValueError: If the provider is not recognized.
        Exception: If the LLM API call fails after retries.
    """
    factory = _CLIENT_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(f"Unknown provider: {provider}")

    client = factory()

    # Construct batch prompt
    news_content = ""
    for chunk in chunks:
        news_content += f"""
---
Source ID: {chunk['source_id']}
Content: {chunk['content']}
---
"""

    prompt = f"""You are a hedge fund trading algorithm. Next you will see a batch of financial news snippets and your current portfolio (if any). 
    Analyze the current portfolio and the news snippets and the state of the market, find trading and investmentideas with a high profit potential.
    look for relevant companies and tickers and determine a trading signal:
    *BUY: Only buy if we don't already have the stock in our portfolio.
    *SELL: Only sell if we have the stock in our portfolio.
    *HOLD: Do not buy or sell the stock.
    You must provide a confidence score (0-100) and your reasoning for each decision.
    Each decision MUST include the exact 'Source ID' of the snippet that triggered it.

### Historical Context (Relevant Past Events):
{context if context else "No relevant historical context found."}

### News Batch:
{news_content}

Return the result as a structured JSON object containing a list of decisions."""

    try:
        from .models import DecisionsResponse

        args = {
            "model": model_name,
            "response_model": DecisionsResponse,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a hedge fund trading algorithm. Analyze news strictly and return a list of decisions."
                },
                {"role": "user", "content": prompt}
            ],
            "max_retries": 2,
        }

        # Anthropic requires max_tokens to be explicitly set
        if provider == "anthropic":
            args["max_tokens"] = 4096  # Increased for batch processing

        print(f"Calling LLM provider: {provider} with model: {model_name}")
        resp_awaitable = client.chat.completions.create(**args)

        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable

        # Return the list of decisions from the container
        return resp.decisions

    except Exception as e:
        logger.error(f"Error analyzing batch with {provider}/{model_name}: {e}")
        raise
