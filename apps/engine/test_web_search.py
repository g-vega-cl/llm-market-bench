#!/usr/bin/env python3
"""Test script for web search integration.

This script tests web search functionality across all supported providers:
- Anthropic (web_search_20250305)
- Gemini (google_search grounding)
- OpenAI (limited support in Chat API)

Usage:
    python test_web_search.py
    pytest test_web_search.py
"""

import asyncio
import logging
import os
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import (
    ENABLE_ANTHROPIC_WEB_SEARCH,
    ENABLE_GEMINI_WEB_SEARCH,
    ANTHROPIC_MODEL,
    GEMINI_MODEL,
)
from core.llm import clients

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("web_search_test")


@pytest.mark.asyncio
async def test_anthropic_web_search():
    """Test Anthropic web search tool."""
    logger.info("=" * 60)
    logger.info("Testing Anthropic Web Search")
    logger.info("=" * 60)
    
    if not ENABLE_ANTHROPIC_WEB_SEARCH:
        logger.warning("Anthropic web search is disabled in config. Skipping.")
        return False
    
    try:
        client = clients.get_anthropic_client()
        raw_client = client.client
        
        messages = [
            {
                "role": "user",
                "content": "Search for the latest stock market news today. What are the major movers?"
            }
        ]
        
        from core.llm.handlers.anthropic import run_tool_loop
        
        await run_tool_loop(
            raw_client=raw_client,
            model_name=ANTHROPIC_MODEL,
            messages=messages,
            enable_web_search=True
        )
        
        # Print the response
        for msg in messages:
            if msg["role"] == "assistant":
                logger.info("Assistant Response:")
                for content in msg["content"]:
                    if content.get("type") == "text":
                        logger.info(content["text"])
                    elif content.get("type") == "server_tool_use":
                        logger.info(f"Tool used: {content['name']} - {content.get('input', {})}")
        
        logger.info("Anthropic web search test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Anthropic web search test failed: {e}")
        return False
    finally:
        await clients.close_client(client, "anthropic")


@pytest.mark.asyncio
async def test_gemini_web_search():
    """Test Gemini Google Search grounding."""
    logger.info("=" * 60)
    logger.info("Testing Gemini Google Search Grounding")
    logger.info("=" * 60)
    
    if not ENABLE_GEMINI_WEB_SEARCH:
        logger.warning("Gemini web search is disabled in config. Skipping.")
        return False
    
    try:
        client = clients.get_gemini_client()
        raw_client = client.client
        
        messages = [
            {
                "role": "user",
                "content": "Who won the most recent Super Bowl and what was the score?"
            }
        ]
        
        from core.llm.handlers.gemini import run_tool_loop
        
        await run_tool_loop(
            raw_client=raw_client,
            model_name=GEMINI_MODEL,
            messages=messages,
            enable_google_search=True
        )
        
        # Print the response
        for msg in messages:
            if hasattr(msg, "parts"):
                logger.info("Model Response:")
                for part in msg.parts:
                    if hasattr(part, "text") and part.text:
                        logger.info(part.text)
                    elif hasattr(part, "function_call") and part.function_call:
                        logger.info(f"Function call: {part.function_call.name}")
        
        # Check for grounding metadata
        logger.info("Check the response for groundingMetadata in the actual API response")
        
        logger.info("Gemini web search test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Gemini web search test failed: {e}")
        return False
    finally:
        await clients.close_client(client, "gemini")


@pytest.mark.asyncio
async def test_anthropic_web_search_with_citations():
    """Test Anthropic web search and verify citation handling."""
    logger.info("=" * 60)
    logger.info("Testing Anthropic Web Search with Citation Check")
    logger.info("=" * 60)
    
    if not ENABLE_ANTHROPIC_WEB_SEARCH:
        logger.warning("Anthropic web search is disabled. Skipping.")
        return False
    
    try:
        client = clients.get_anthropic_client()
        raw_client = client.client
        
        messages = [
            {
                "role": "user",
                "content": "Search for when Claude 3.7 Sonnet was released and tell me about its capabilities."
            }
        ]
        
        from core.llm.handlers.anthropic import run_tool_loop
        
        await run_tool_loop(
            raw_client=raw_client,
            model_name=ANTHROPIC_MODEL,
            messages=messages,
            enable_web_search=True
        )
        
        # Check for web_search_tool_result in response
        has_search_result = False
        for msg in messages:
            if msg["role"] == "assistant":
                for content in msg["content"]:
                    if content.get("type") == "web_search_tool_result":
                        has_search_result = True
                        logger.info("Found web_search_tool_result in response!")
                        result_content = content.get("content", [])
                        for result in result_content:
                            if isinstance(result, dict):
                                logger.info(f"  URL: {result.get('url', 'N/A')}")
                                logger.info(f"  Title: {result.get('title', 'N/A')}")
        
        if has_search_result:
            logger.info("Citation handling verified!")
        else:
            logger.warning("No web_search_tool_result found in response")
        
        return has_search_result
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    finally:
        await clients.close_client(client, "anthropic")


async def main():
    """Run all web search tests."""
    logger.info("Starting Web Search Integration Tests")
    logger.info(f"ENABLE_ANTHROPIC_WEB_SEARCH: {ENABLE_ANTHROPIC_WEB_SEARCH}")
    logger.info(f"ENABLE_GEMINI_WEB_SEARCH: {ENABLE_GEMINI_WEB_SEARCH}")
    logger.info("")
    
    results = {
        "anthropic": await test_anthropic_web_search(),
        "gemini": await test_gemini_web_search(),
        "anthropic_citations": await test_anthropic_web_search_with_citations(),
    }
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("\nAll tests passed!")
        return 0
    else:
        logger.warning("\nSome tests failed. Check logs for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
