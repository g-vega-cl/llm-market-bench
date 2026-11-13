"""Unit tests for the observation-only SSE stream auditor."""

from __future__ import annotations

import time

import pytest

from apps.free_llm_proxy.streaming import audited_sse_stream


async def _collect(source, started_at=None, **kwargs):
    captured: list[dict] = []

    def on_complete(result):
        captured.append(result)

    chunks = [
        chunk
        async for chunk in audited_sse_stream(
            source, on_complete, started_at=started_at, **kwargs
        )
    ]
    return chunks, captured[0] if captured else None


@pytest.mark.asyncio
async def test_stream_usage_captured_and_bytes_unchanged():
    """Usage is captured without changing a single SSE byte."""
    chunks = [
        b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
        b'data: {"choices": [], "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}}\n\n',
        b"data: [DONE]\n\n",
    ]

    async def source():
        for chunk in chunks:
            yield chunk

    out, result = await _collect(source(), started_at=time.perf_counter())

    assert out == chunks
    assert result is not None
    assert result["usage"]["total_tokens"] == 18
    assert result["completed"] is True
    assert result["error"] is None
    assert result["ttft_ms"] >= 0
    assert result["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_stream_usage_parsed_across_chunk_boundaries():
    """An SSE line split across TCP chunks is still parsed."""
    chunks = [
        b'data: {"choices": [], "usage": {"prompt_tokens": 5,',
        b'"completion_tokens": 3, "total_tokens": 8}}\n\n',
        b"data: [DONE]\n\n",
    ]

    async def source():
        for chunk in chunks:
            yield chunk

    out, result = await _collect(source())

    assert out == chunks
    assert result["usage"]["total_tokens"] == 8
    assert result["completed"] is True


@pytest.mark.asyncio
async def test_malformed_sse_does_not_break_stream():
    """Malformed or unrelated SSE lines never raise or alter the stream."""
    chunks = [
        b"event: ping\n\n",
        b"data: not-json\n\n",
        b'data: {"choices": [{"delta": {"content": "OK"}}]}\n\n',
        b"data: [DONE]\n\n",
    ]

    async def source():
        for chunk in chunks:
            yield chunk

    out, result = await _collect(source())

    assert out == chunks
    assert result["usage"] is None
    assert result["completed"] is True


@pytest.mark.asyncio
async def test_stream_error_is_reported_without_hiding_chunks():
    """A provider mid-stream failure is logged as incomplete, not as success."""
    chunks = [b'data: {"choices": [{"delta": {"content": "partial"}}]}\n\n']
    captured: list[dict] = []

    async def source():
        for chunk in chunks:
            yield chunk
        raise RuntimeError("provider dropped")

    def on_complete(result):
        captured.append(result)

    received = []
    with pytest.raises(RuntimeError, match="provider dropped"):
        async for chunk in audited_sse_stream(source(), on_complete):
            received.append(chunk)

    assert received == chunks
    assert captured[0]["completed"] is False
    assert "RuntimeError" in captured[0]["error"]


@pytest.mark.asyncio
async def test_telemetry_callback_failure_does_not_break_stream():
    """A failing audit callback must never break the client stream."""
    chunks = [b"data: [DONE]\n\n"]

    async def source():
        for chunk in chunks:
            yield chunk

    def on_complete(_result):
        raise RuntimeError("audit database unavailable")

    out = [chunk async for chunk in audited_sse_stream(source(), on_complete)]
    assert out == chunks


@pytest.mark.asyncio
async def test_stream_parse_buffer_is_bounded(monkeypatch):
    """Oversized SSE lines stop parsing but still pass through unchanged."""
    monkeypatch.setattr("apps.free_llm_proxy.streaming.MAX_PARSE_BUFFER_BYTES", 16)
    chunks = [
        b"data: " + b"x" * 100 + b"\n\n",
        b"data: [DONE]\n\n",
    ]

    async def source():
        for chunk in chunks:
            yield chunk

    out, result = await _collect(source())

    assert out == chunks
    assert result["usage"] is None
