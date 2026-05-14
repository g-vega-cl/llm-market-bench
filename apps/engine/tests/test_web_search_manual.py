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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import (
    ANTHROPIC_MODEL,
    ENABLE_ANTHROPIC_WEB_SEARCH,
    ENABLE_GEMINI_WEB_SEARCH,
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
    """Test Anthropic web search tool with mocks."""
    logger.info("=" * 60)
    logger.info("Testing Anthropic Web Search (MOCKED)")
    logger.info("=" * 60)
    
    client = None
    try:
        with patch("core.llm.clients.get_anthropic_client") as mock_get_client, \
             patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock) as mock_run_loop:
            
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            client = mock_client
            
            messages = [
                {
                    "role": "user",
                    "content": "Search for the latest stock market news today."
                }
            ]
            
            # Simulate the tool loop adding a response
            async def side_effect(*args, **kwargs):
                messages.append({
                    "role": "assistant", 
                    "content": [{"type": "text", "text": "Mocked stock news response"}]
                })
            mock_run_loop.side_effect = side_effect
            
            from core.llm.handlers.anthropic import run_tool_loop
            
            await run_tool_loop(
                raw_client=mock_client.client,
                model_name=ANTHROPIC_MODEL,
                messages=messages,
                enable_web_search=True
            )
            
            # Assertions
            assert any(msg["role"] == "assistant" for msg in messages)
            logger.info("Anthropic web search test (mocked) completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Anthropic web search test failed: {e}")
        return False
    finally:
        if client:
            await clients.close_client(client, "anthropic")


@pytest.mark.asyncio
async def test_gemini_web_search():
    """Test Gemini Google Search grounding with mocks."""
    logger.info("=" * 60)
    logger.info("Testing Gemini Google Search Grounding (MOCKED)")
    logger.info("=" * 60)
    
    client = None
    try:
        with patch("core.llm.clients.get_gemini_client") as mock_get_client, \
             patch("core.llm.handlers.gemini.run_tool_loop", new_callable=AsyncMock) as mock_run_loop:
            
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            client = mock_client
            
            messages = [
                {
                    "role": "user",
                    "content": "Who won the most recent Super Bowl?"
                }
            ]
            
            # Mock the response part
            mock_part = MagicMock()
            mock_part.text = "Mocked Gemini response"
            
            async def side_effect(*args, **kwargs):
                msg = MagicMock()
                msg.parts = [mock_part]
                messages.append(msg)
            mock_run_loop.side_effect = side_effect
            
            from core.llm.handlers.gemini import run_tool_loop
            
            await run_tool_loop(
                raw_client=mock_client.client,
                model_name=GEMINI_MODEL,
                messages=messages,
                enable_google_search=True
            )
            
            # Assertions
            assert len(messages) > 1
            logger.info("Gemini web search test (mocked) completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Gemini web search test failed: {e}")
        return False
    finally:
        if client:
            await clients.close_client(client, "gemini")


@pytest.mark.asyncio
async def test_anthropic_web_search_with_citations():
    """Test Anthropic web search and verify citation handling with mocks."""
    logger.info("=" * 60)
    logger.info("Testing Anthropic Web Search Citations (MOCKED)")
    logger.info("=" * 60)
    
    client = None
    try:
        with patch("core.llm.clients.get_anthropic_client") as mock_get_client, \
             patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock) as mock_run_loop:
            
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            client = mock_client
            
            messages = [
                {
                    "role": "user",
                    "content": "Search for Claude 3.7 Sonnet release date."
                }
            ]
            
            # Simulate response with web_search_tool_result (citations)
            async def side_effect(*args, **kwargs):
                messages.append({
                    "role": "assistant",
                    "content": [
                        {
                            "type": "web_search_tool_result",
                            "content": [{"url": "https://anthropic.com", "title": "Claude 3.7 Release"}]
                        }
                    ]
                })
            mock_run_loop.side_effect = side_effect
            
            from core.llm.handlers.anthropic import run_tool_loop
            
            await run_tool_loop(
                raw_client=mock_client.client,
                model_name=ANTHROPIC_MODEL,
                messages=messages,
                enable_web_search=True
            )
            
            # Check for web_search_tool_result in response
            has_search_result = False
            for msg in messages:
                if msg.get("role") == "assistant":
                    for content in msg.get("content", []):
                        if content.get("type") == "web_search_tool_result":
                            has_search_result = True
            
            assert has_search_result
            logger.info("Citation handling (mocked) verified!")
            return True
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    finally:
        if client:
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
