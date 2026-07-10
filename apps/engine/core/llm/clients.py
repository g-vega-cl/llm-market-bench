"""LLM client factories and registry."""

import inspect
import logging

import instructor
from anthropic import AsyncAnthropic
from google import genai
from openai import AsyncOpenAI

from core import config

logger = logging.getLogger("engine")

TIMEOUT = 180


def get_openai_client(api_key: str | None = None):
    """Creates an async OpenAI client wrapped with Instructor."""
    key = api_key or config.OPENAI_API_KEY
    return instructor.from_openai(AsyncOpenAI(api_key=key, timeout=TIMEOUT))


def get_anthropic_client(api_key: str | None = None):
    """Creates an async Anthropic client wrapped with Instructor."""
    key = api_key or config.ANTHROPIC_API_KEY
    return instructor.from_anthropic(AsyncAnthropic(api_key=key, timeout=TIMEOUT))


def get_deepseek_client(api_key: str | None = None):
    """Creates an async DeepSeek client wrapped with Instructor.

    Uses the OpenAI SDK to interact with DeepSeek's API.
    """
    key = api_key or config.DEEPSEEK_API_KEY
    return instructor.from_openai(
        AsyncOpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=TIMEOUT),
        mode=instructor.Mode.MD_JSON,
    )


def get_gemini_client(api_key: str | None = None):
    """Creates a Google Gemini client wrapped with Instructor.

    Uses mode=GENAI_TOOLS to properly handle Gemini's function calling.
    """
    import asyncio

    key = api_key or config.GEMINI_API_KEY
    client = genai.Client(api_key=key)
    instr_client = instructor.from_genai(client, mode=instructor.Mode.GENAI_TOOLS)

    original_create = instr_client.chat.completions.create

    from unittest.mock import Mock

    if not isinstance(original_create, Mock):

        async def async_create(*args, **kwargs):
            return await asyncio.to_thread(original_create, *args, **kwargs)

        instr_client.chat.completions.create = async_create
    return instr_client


def get_minimax_client(api_key: str | None = None):
    """Creates an async MiniMax client wrapped with Instructor.

    Uses the Anthropic SDK pointed at MiniMax's Anthropic-compatible endpoint.
    M3 supports both OpenAI- and Anthropic-compatible APIs; the Anthropic
    format gives us native tool_use blocks, proper thinking control, and
    compatibility with our existing anthropic tool-loop handler.

    The OpenAI-format endpoint is still used by auxiliary flows
    (market_feeling, sector_predictor) via core.llm.minimax.MiniMaxClient.
    """
    key = api_key or config.MINIMAX_API_KEY
    return instructor.from_anthropic(
        AsyncAnthropic(
            api_key=key,
            base_url=config.MINIMAX_ANTHROPIC_BASE_URL,
            timeout=TIMEOUT,
        ),
        mode=instructor.Mode.ANTHROPIC_JSON,
    )


# Provider Registry
# NOTE: This dict is populated at import time with function references to the
# factories above. Tests must patch `CLIENT_FACTORIES` (not the individual
# factory functions), because patching `core.llm.clients.get_*_client` only
# replaces the module attribute — the dict still holds the originals and
# `verify_trading_decision` (and other callers) will invoke the real factory,
# which constructs a real SDK client that fails on missing credentials in CI.
# See tests/test_verification.py for the established pattern.
CLIENT_FACTORIES = {
    "openai": get_openai_client,
    "anthropic": get_anthropic_client,
    "deepseek": get_deepseek_client,
    "gemini": get_gemini_client,
    "minimax": get_minimax_client,
}


async def close_client(client, provider: str):
    """Safely closes an instructor-wrapped LLM client.

    Args:
        client: The instructor-wrapped client instance.
        provider: The provider name for logging purposes.
    """
    if client is None:
        return

    try:
        # Instructor wraps clients but preserves the underlying client reference
        if hasattr(client, "client"):
            underlying = client.client
            if underlying is None:
                logger.debug("Cannot close %s client: underlying client is None", provider)
                return
            if hasattr(underlying, "close"):
                close_method = underlying.close
                if inspect.iscoroutinefunction(close_method):
                    await close_method()
                else:
                    close_method()
            elif hasattr(underlying, "_async_httpx_client") and underlying._async_httpx_client is not None:
                await underlying._async_httpx_client.aclose()
            else:
                logger.debug("No close method found for %s client", provider)
    except Exception as e:
        logger.warning("Failed to close %s client: %s", provider, repr(e))
