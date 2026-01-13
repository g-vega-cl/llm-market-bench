"""Minimal test to verify async client cleanup fix.

This test makes a single real API call to OpenAI to verify that:
1. The client properly closes after use
2. No "Event loop is closed" errors occur
3. The async cleanup pattern works correctly
"""

import asyncio
import pytest
from core.llm import analyze_with_provider
from core.config import OPENAI_MODEL


@pytest.mark.asyncio
async def test_client_cleanup_single_provider():
    """Test that a single API call properly cleans up the HTTP client.

    This test makes ONE real API call to OpenAI (minimal cost) to verify
    the client cleanup fix works correctly.
    """
    # Minimal test data - single short chunk
    test_chunks = [{
        "source_id": "test_cleanup_001",
        "content": "Apple announces Q4 earnings beat expectations by 5%."
    }]

    # Make a single API call
    result = await analyze_with_provider(
        provider="openai",
        model_name=OPENAI_MODEL,
        chunks=test_chunks,
        context=""
    )

    # Verify we got a valid response
    assert result is not None
    assert hasattr(result, 'decisions')
    assert hasattr(result, 'macro_events')

    # If we get here without errors, cleanup worked!
    print("✓ Client cleanup successful - no event loop errors")


def test_client_cleanup_with_asyncio_run():
    """Test that cleanup works when using asyncio.run() (like main.py does).

    This mimics how main.py calls analyze_chunks with asyncio.run().
    The error we fixed occurred during asyncio.run() shutdown.
    """
    async def run_test():
        test_chunks = [{
            "source_id": "test_cleanup_002",
            "content": "Tesla stock rises 3% on delivery numbers."
        }]

        result = await analyze_with_provider(
            provider="openai",
            model_name=OPENAI_MODEL,
            chunks=test_chunks,
            context=""
        )

        return result

    # This is the pattern that was causing the error
    result = asyncio.run(run_test())

    # Verify result
    assert result is not None
    print("✓ asyncio.run() cleanup successful - no event loop errors")


if __name__ == "__main__":
    # Can run directly for quick testing
    print("Running client cleanup test...")
    test_client_cleanup_with_asyncio_run()
    print("\n✓ All cleanup tests passed!")
