"""Regression tests ensuring test suite latency guards eliminate artificial sleeps."""

import time
from unittest.mock import MagicMock

import pytest

import memory.store
from execution.providers.massive import _MASSIVE_LIMITER
from memory.embeddings import _call_embed_with_retry
from memory.store import retrieve_for_decision


@pytest.mark.asyncio
async def test_massive_limiter_instant_in_test_env():
    """Verify that _MASSIVE_LIMITER.acquire does not block for 12s per token in tests."""
    start = time.perf_counter()
    # 10 calls on a 5-token bucket with refill rate 1/12s would take >= 60s if not bypassed
    for _ in range(10):
        await _MASSIVE_LIMITER.acquire()
    duration = time.perf_counter() - start

    assert duration < 0.1, f"Limiter acquire took {duration:.2f}s; expected < 0.1s"


def test_store_embeddings_instant_and_deterministic_by_default():
    """Verify that memory.store embedding lookup completes immediately with deterministic vector."""
    start = time.perf_counter()
    vector = memory.store.get_embedding("test query text")
    duration = time.perf_counter() - start

    assert duration < 0.1, f"get_embedding took {duration:.2f}s; expected < 0.1s"
    assert len(vector) == 768
    assert vector[0] == 0.1


def test_retrieve_for_decision_instant_by_default():
    """Verify that retrieve_for_decision does not trigger live API retries or delay tests."""
    start = time.perf_counter()
    # In unmocked state with live API or blocked socket, this took 16.7s
    result = retrieve_for_decision(ticker="NVDA", reasoning="Strong momentum and margins")
    duration = time.perf_counter() - start

    assert duration < 0.2, f"retrieve_for_decision took {duration:.2f}s; expected < 0.2s"
    assert isinstance(result, str)


def test_call_embed_with_retry_does_not_retry_runtime_error():
    """Verify that _call_embed_with_retry fails fast on socket-block RuntimeError instead of retrying."""
    mock_client = MagicMock()
    mock_client.models.embed_content.side_effect = RuntimeError("External network connection blocked during test")

    start = time.perf_counter()
    with pytest.raises(RuntimeError, match="External network connection blocked"):
        _call_embed_with_retry(
            client=mock_client,
            model="models/text-embedding-004",
            contents=["test"],
            config={"output_dimensionality": 768},
        )
    duration = time.perf_counter() - start

    # If tenacity retried 4 times, duration would be >= 16s
    assert duration < 0.5, f"_call_embed_with_retry retried RuntimeError for {duration:.2f}s; expected < 0.5s"
    assert mock_client.models.embed_content.call_count == 1
