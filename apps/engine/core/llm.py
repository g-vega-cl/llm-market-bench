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
    text: str,
    source_id: str,
    context: str = ""
) -> DecisionObject:
    """Analyzes text using the specified provider and returns a DecisionObject.

    Args:
        provider: The LLM provider name (openai, anthropic, gemini, deepseek).
        model_name: The specific model identifier for the provider.
        text: The financial news text to analyze.
        source_id: The unique identifier of the source newsletter chunk.

    Returns:
        A DecisionObject containing the trading signal, confidence, and reasoning.

    Raises:
        ValueError: If the provider is not recognized.
        Exception: If the LLM API call fails after retries.
    """
    factory = _CLIENT_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(f"Unknown provider: {provider}")

    client = factory()

    prompt = f"""Analyze the following financial news snippet and determine a trading signal (BUY, SELL, HOLD) for the relevant ticker.
You must provide a confidence score (0-100) and your reasoning.
The source_id for this news is: {source_id}

### Historical Context (Relevant Past Events):
{context if context else "No relevant historical context found."}

### News Snippet:
"{text}"

Return the result as a structured JSON object matching the schema."""

    try:
        args = {
            "model": model_name,
            "response_model": DecisionObject,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a hedge fund trading algorithm. Analyze news strictly."
                },
                {"role": "user", "content": prompt}
            ],
            "max_retries": 2,
        }

        # Anthropic requires max_tokens to be explicitly set
        if provider == "anthropic":
            args["max_tokens"] = 1024

        resp_awaitable = client.chat.completions.create(**args)

        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable

        return resp

    except Exception as e:
        logger.error(f"Error analyzing with {provider}/{model_name}: {e}")
        raise
