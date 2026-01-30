"""LLM client factories and registry."""

import logging

import instructor
from anthropic import AsyncAnthropic
from google import genai
from openai import AsyncOpenAI

from core import config

logger = logging.getLogger("engine")

TIMEOUT = 180

def get_openai_client():
    """Creates an async OpenAI client wrapped with Instructor."""
    return instructor.from_openai(AsyncOpenAI(
        api_key=config.OPENAI_API_KEY,
        timeout=TIMEOUT
    ))


def get_anthropic_client():
    """Creates an async Anthropic client wrapped with Instructor."""
    return instructor.from_anthropic(AsyncAnthropic(
        api_key=config.ANTHROPIC_API_KEY,
        timeout=TIMEOUT
    ))


def get_deepseek_client():
    """Creates an async DeepSeek client wrapped with Instructor.

    Uses the OpenAI SDK to interact with DeepSeek's API.
    """
    return instructor.from_openai(
        AsyncOpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            timeout=TIMEOUT
        ),
        mode=instructor.Mode.JSON
    )


def get_gemini_client():
    """Creates a Google Gemini client wrapped with Instructor."""
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    return instructor.from_genai(client)


# Provider Registry
CLIENT_FACTORIES = {
    "openai": get_openai_client,
    "anthropic": get_anthropic_client,
    "deepseek": get_deepseek_client,
    "gemini": get_gemini_client,
}


async def close_client(client, provider: str):
    """Safely closes an instructor-wrapped LLM client.

    Args:
        client: The instructor-wrapped client instance.
        provider: The provider name for logging purposes.
    """
    try:
        # Instructor wraps clients but preserves the underlying client reference
        if hasattr(client, "client"):
            underlying = client.client
            if hasattr(underlying, "close"):
                await underlying.close()
            elif hasattr(underlying, "_async_httpx_client"):
                await underlying._async_httpx_client.aclose()
    except Exception as e:
        logger.debug("Failed to close %s client: %s", provider, e)
