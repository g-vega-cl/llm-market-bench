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
from pydantic import BaseModel

from . import config
from .models import DecisionObject, DecisionsResponse

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


# --- Client Cleanup Helper ---

async def _close_client(client, provider: str):
    """Safely closes an instructor-wrapped LLM client.

    Args:
        client: The instructor-wrapped client instance.
        provider: The provider name for logging purposes.
    """
    try:
        # Instructor wraps clients but preserves the underlying client reference
        if hasattr(client, 'client'):
            underlying = client.client
            if hasattr(underlying, 'close'):
                await underlying.close()
            elif hasattr(underlying, '_async_httpx_client'):
                await underlying._async_httpx_client.aclose()
    except Exception as e:
        logger.debug(f"Failed to close {provider} client: {e}")


# --- Analysis Functions ---

async def analyze_with_provider(
    provider: str,
    model_name: str,
    chunks: list[dict],
    context: str = ""
) -> DecisionsResponse:
    """Analyzes a batch of newsletter chunks using the specified provider.

    Args:
        provider: The LLM provider name (openai, anthropic, gemini, deepseek).
        model_name: The specific model identifier for the provider.
        chunks: List of dictionaries containing 'source_id' and 'content'.
        context: Aggregated historical context.

    Returns:
        A DecisionsResponse instance containing trading signals and macro events.

    Raises:
        ValueError: If the provider is not recognized.
        Exception: If the LLM API call fails after retries.
    """
    factory = _CLIENT_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(f"Unknown provider: {provider}")

    client = factory()

    try:
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
        Analyze the current portfolio and the news snippets and the state of the market, find trading and investment ideas with a high profit potential.

        1. Trading Signals: Look for relevant companies and tickers and determine a trading signal:
           * BUY: Only buy if we don't already have the stock in our portfolio.
           * SELL: Only sell if we have the stock in our portfolio.
           * HOLD: Do not buy or sell the stock.
           Each decision MUST include the exact 'Source ID' of the snippet that triggered it.

        2. Macro Events: Identify major global themes, macro-economic shifts, or significant events mentioned in the news (e.g., "Fed Rate Hike", "AI Demand Surge", "Geopolitical Tension").
           For each theme, determine if it is BULLISH, BEARISH, or NEUTRAL for the overall market and provide your reasoning.
           Each macro event MUST include the exact 'Source ID' of the snippet that triggered it.

        You must provide a confidence score (0-100) and your reasoning for each trading signal and macro event.

### Historical Context (Relevant Past Events):
{context if context else "No relevant historical context found."}

### News Batch:
{news_content}

Return the result as a structured JSON object containing a list of 'decisions' and a list of 'macro_events'."""

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
            args["max_tokens"] = 8000  # Increased for batch processing

        print(f"Calling LLM provider: {provider} with model: {model_name}")
        resp_awaitable = client.chat.completions.create(**args)

        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable

        # Return the complete response container
        return resp

    except Exception as e:
        logger.error(f"Error analyzing batch with {provider}/{model_name}: {e}")
        raise
    finally:
        # Ensure client is properly closed
        await _close_client(client, provider)


async def synthesize_event(
    event_name: str,
    impact: str,
    reasonings: list[str]
) -> dict[str, str]:
    """Synthesizes a unified event name and summary from multiple model perspectives.

    Args:
        event_name: The raw representative event name.
        impact: The majority impact (BULLISH/BEARISH/NEUTRAL).
        reasonings: A list of reasoning strings from different models.

    Returns:
        A dictionary with 'name' and 'summary' keys.
    """
    client = get_openai_client()  # Using OpenAI for synthesis as it's reliable for this

    try:
        combined_reasonings = "\n".join([f"- {r}" for r in reasonings])

        prompt = f"""You are a senior financial analyst. Synthesize the following event reports into a single, professional market event entry.

        RAW EVENT NAME: {event_name}
        IMPACT: {impact}
        MODEL OBSERVATIONS:
        {combined_reasonings}

        Your task:
        1. Create a professional, concise 'name' for this event (max 5 words).
        2. Write a 1-sentence 'summary' that captures the core catalyst and market implication.

        Return ONLY a JSON object with 'name' and 'summary' keys."""

        class SynthesisResponse(BaseModel):
            name: str
            summary: str

        resp = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            response_model=SynthesisResponse,
            messages=[
                {"role": "system", "content": "You are a senior financial analyst. Return structured JSON."},
                {"role": "user", "content": prompt}
            ],
            max_retries=2
        )
        return {"name": resp.name, "summary": resp.summary}
    except Exception as e:
        logger.error(f"Event synthesis failed: {e}")
        # Fallback to original if synthesis fails
        return {
            "name": event_name,
            "summary": f"Consensus reached on {event_name} with {impact} impact based on model observations."
        }
    finally:
        # Ensure client is properly closed
        await _close_client(client, "openai")
