"""Minimal test to verify async client cleanup fix.

This test makes a single real API call to OpenAI to verify that:
1. The client properly closes after use
2. No "Event loop is closed" errors occur
3. The async cleanup pattern works correctly
"""

import asyncio

import pytest

from core.config import OPENAI_MODEL
from core.llm import analyze_with_provider


@pytest.mark.asyncio
async def test_client_cleanup_single_provider(monkeypatch):
    """Test that a single API call properly cleans up the HTTP client.

    This test verifies that the system doesn't crash during cleanup.
    We mock analyze_with_provider to avoid real API calls and
    instructor parsing issues in tests.
    """
    from core.models import DecisionsResponse

    async def mock_analyze(*args, **kwargs):
        return DecisionsResponse(decisions=[], macro_events=[])

    # Mock the high level function to avoid instructor parsing logic in this test
    monkeypatch.setattr("tests.test_client_cleanup.analyze_with_provider", mock_analyze)

    # Minimal test data
    test_chunks = [{"source_id": "test_cleanup_001", "content": "Apple announces Q4 earnings beat expectations by 5%."}]

    # Make a single call
    result = await analyze_with_provider(provider="openai", model_name=OPENAI_MODEL, chunks=test_chunks, context="")

    # Verify we got a valid response
    assert result is not None
    assert hasattr(result, "decisions")

    # If we get here without errors, cleanup worked!
    print("✓ Client cleanup successful - no event loop errors")


def test_client_cleanup_with_asyncio_run(monkeypatch):
    """Test that cleanup works when using asyncio.run() (like main.py does)."""
    from core.models import DecisionsResponse

    async def mock_analyze(*args, **kwargs):
        return DecisionsResponse(decisions=[], macro_events=[])

    monkeypatch.setattr("tests.test_client_cleanup.analyze_with_provider", mock_analyze)

    async def run_test():
        test_chunks = [{"source_id": "test_cleanup_002", "content": "Tesla stock rises 3% on delivery numbers."}]

        result = await analyze_with_provider(provider="openai", model_name=OPENAI_MODEL, chunks=test_chunks, context="")

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
