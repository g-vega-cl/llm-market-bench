"""TDD: a truncated upstream stream must never reach the client as a bare EOF.

Reproduces the "Error: Stream ended without finish_reason" storm on pi/auto-go:

  * providers that close the SSE stream after one chunk (or drop the TCP
    connection) leave strict OpenAI clients with no terminal chunk at all;
  * because the proxy has already emitted 200 + headers it could not fail over,
    so the failure surfaced client-side instead of being retried;
  * the audit DB still recorded the call as ``stream_completed = 1``.

The contract under test: a streaming response always ends with a chunk carrying
a non-null ``finish_reason`` plus ``data: [DONE]``, providers that die before the
first token are failed over transparently, and every truncation is recorded as an
incomplete stream (and counted against the provider's circuit breaker).
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from apps.free_llm_proxy.circuit_breaker import CircuitBreaker
from apps.free_llm_proxy.config import load_providers_config
from apps.free_llm_proxy.db import AuditDB
from apps.free_llm_proxy.streaming import (
    audited_sse_stream,
    prefixed_stream,
    prime_sse_stream,
)
from apps.free_llm_proxy.tests.limit_helpers import (
    HEADERS,
    install_catalog,
    install_chain,
    provider_cfg,
)

CONTENT_CHUNK = b'data: {"id": "gen-1", "model": "m", "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": null}]}\n\n'
ROLE_ONLY_CHUNK = b'data: {"id": "gen-1", "model": "m", "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": null}]}\n\n'
FINISH_CHUNK = b'data: {"id": "gen-1", "model": "m", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}\n\n'
DONE_CHUNK = b"data: [DONE]\n\n"


def _events(payload: bytes) -> list[str]:
    return [
        line
        for line in payload.decode("utf-8", "replace").splitlines()
        if line.startswith("data:")
    ]


def _finish_reasons(payload: bytes) -> list[str]:
    reasons = []
    for event in _events(payload):
        body = event[5:].strip()
        if body == "[DONE]":
            continue
        try:
            obj = json.loads(body)
        except json.JSONDecodeError:
            continue
        for choice in obj.get("choices") or []:
            if choice.get("finish_reason"):
                reasons.append(choice["finish_reason"])
    return reasons


async def _drain(source, **kwargs):
    captured: list[dict] = []

    def on_complete(result):
        captured.append(result)

    out: list[bytes] = []
    async for chunk in audited_sse_stream(
        source, on_complete, started_at=time.perf_counter(), **kwargs
    ):
        out.append(chunk)
    return b"".join(out), captured[0]


# --------------------------------------------------------------------------- #
# Auditor: terminal-chunk guarantee
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_complete_stream_passes_through_byte_identical():
    """A stream that already terminates is never rewritten."""
    chunks = [CONTENT_CHUNK, FINISH_CHUNK, DONE_CHUNK]

    async def source():
        for chunk in chunks:
            yield chunk

    body, result = await _drain(source())

    assert body == b"".join(chunks)
    assert _finish_reasons(body) == ["stop"]
    assert result["completed"] is True
    assert result["truncated"] is False


@pytest.mark.asyncio
async def test_done_without_finish_reason_gains_a_terminal_chunk():
    """`data: [DONE]` alone is not a terminal chunk for strict clients."""
    chunks = [CONTENT_CHUNK, DONE_CHUNK]

    async def source():
        for chunk in chunks:
            yield chunk

    body, result = await _drain(source())

    assert body.count(b"[DONE]") == 1
    assert _events(body)[-1] == "data: [DONE]"
    assert _finish_reasons(body) == ["length"]
    assert result["truncated"] is True
    assert result["completed"] is False
    assert "truncated" in (result["error"] or "").lower()


@pytest.mark.asyncio
async def test_clean_eof_without_any_marker_gains_a_terminal_chunk():
    """A provider that just stops talking still yields a well-formed stream."""
    chunks = [ROLE_ONLY_CHUNK, CONTENT_CHUNK]

    async def source():
        for chunk in chunks:
            yield chunk

    body, result = await _drain(source())

    assert _finish_reasons(body) == ["length"]
    assert body.endswith(DONE_CHUNK)
    assert result["truncated"] is True
    assert result["completed"] is False


@pytest.mark.asyncio
async def test_upstream_exception_becomes_a_terminal_chunk():
    """A mid-stream provider failure is relayed as a truncated completion."""
    chunks = [CONTENT_CHUNK]

    async def source():
        for chunk in chunks:
            yield chunk
        raise RuntimeError("provider dropped")

    body, result = await _drain(source())

    assert body.startswith(b"".join(chunks))
    assert _finish_reasons(body) == ["length"]
    assert result["truncated"] is True
    assert result["completed"] is False
    assert "provider dropped" in (result["error"] or "")


# --------------------------------------------------------------------------- #
# Router: fail over when the provider dies before the first token
# --------------------------------------------------------------------------- #


class _FreshIterator:
    """Iterator over a fixed list; each ``__aiter__`` mints a new one (see below)."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = iter(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._chunks)
        except StopIteration:  # noqa: B904 - async protocol requires this mapping
            raise StopAsyncIteration from None


class _ReIterableSource:
    """Async iterable that returns a *fresh* iterator from every ``__aiter__``.

    Nothing in the streaming path may re-enter ``__aiter__`` after priming, or the
    already-consumed head would be replayed to the client.
    """

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def __aiter__(self):
        return _FreshIterator(self._chunks)


@pytest.mark.asyncio
async def test_primed_head_is_not_duplicated_for_re_iterable_sources():
    source = _ReIterableSource([CONTENT_CHUNK, FINISH_CHUNK, DONE_CHUNK])

    buffered, upstream, produced = await prime_sse_stream(source)
    body = b"".join([chunk async for chunk in prefixed_stream(buffered, upstream)])

    assert produced is True
    assert body.count(b"Hello") == 1
    assert _finish_reasons(body) == ["stop"]


# --------------------------------------------------------------------------- #
# Framing robustness: the terminal repair must not depend on transport framing
# --------------------------------------------------------------------------- #


async def _relay(chunks: list[bytes], **kwargs) -> tuple[bytes, dict]:
    async def source():
        for chunk in chunks:
            yield chunk

    return await _drain(source(), **kwargs)


@pytest.mark.asyncio
async def test_done_marker_split_across_chunks_is_repaired():
    """httpx splits on TCP boundaries, not SSE events: a split [DONE] still closes."""
    body, result = await _relay([CONTENT_CHUNK, b"data: [DO", b"NE]\n\n"])

    assert body.count(b"[DONE]") == 1
    assert _finish_reasons(body) == ["length"]
    assert result["truncated"] is True


@pytest.mark.asyncio
async def test_done_marker_split_one_byte_at_a_time_is_repaired():
    marker = b"data: [DONE]\n\n"
    body, result = await _relay([CONTENT_CHUNK] + [bytes([byte]) for byte in marker])

    assert body.count(b"[DONE]") == 1
    assert _finish_reasons(body) == ["length"]
    assert result["truncated"] is True


@pytest.mark.asyncio
async def test_done_marker_without_space_is_repaired():
    body, _result = await _relay([CONTENT_CHUNK, b"data:[DONE]\n\n"])

    assert body.count(b"[DONE]") == 1
    assert _finish_reasons(body) == ["length"]


@pytest.mark.asyncio
async def test_content_containing_the_done_marker_is_not_corrupted():
    """Model prose must never be mistaken for the terminator."""
    quoted = (
        b'data: {"id": "gen-1", "model": "m", "choices": [{"index": 0, '
        b'"delta": {"content": "write data: [DONE] to finish"}, "finish_reason": null}]}\n\n'
    )
    body, result = await _relay([quoted, FINISH_CHUNK, DONE_CHUNK])

    assert b"write data: [DONE] to finish" in body
    assert _finish_reasons(body) == ["stop"]
    assert [event for event in _events(body) if event.strip() == "data: [DONE]"] == [
        "data: [DONE]"
    ]
    assert result["truncated"] is False
    assert result["completed"] is True


@pytest.mark.asyncio
async def test_unterminated_final_event_is_not_fused_with_the_repair():
    """A provider whose last write lacks the blank line must not get glued to ours."""
    unterminated = (
        b'data: {"id": "gen-1", "model": "m", "choices": [{"index": 0, "delta": {},'
        b' "finish_reason": "stop"}]}'
    )

    body, result = await _relay([CONTENT_CHUNK, unterminated])

    assert _finish_reasons(body) == ["stop"]
    for line in body.decode("utf-8").splitlines():
        if not line.startswith("data:") or line == "data: [DONE]":
            continue
        json.loads(line[5:].strip())  # every frame must be independently parseable
    assert body.count(b"[DONE]") == 1
    assert result["truncated"] is False
    assert result["completed"] is True


@pytest.mark.asyncio
async def test_finish_reason_without_done_gets_the_terminator():
    body, result = await _relay([CONTENT_CHUNK, FINISH_CHUNK])

    assert _finish_reasons(body) == ["stop"]
    assert body.endswith(DONE_CHUNK)
    assert result["truncated"] is False
    assert result["completed"] is True


@pytest.mark.asyncio
async def test_oversized_event_is_reported_as_degraded():
    """When framing is impossible the row must say so, not look like a success."""
    # An event that never terminates: the scanner cannot frame it, so it must
    # degrade explicitly instead of silently shipping an unterminated stream.
    huge = b'data: {"choices": [{"delta": {"content": "' + b"x" * 4096

    body, result = await _relay([huge, DONE_CHUNK], max_buffer_bytes=512)

    assert huge in body  # bytes still relayed
    assert result["truncated"] is True
    assert result["completed"] is False
    assert "degraded" in (result["error"] or "").lower()


@pytest.mark.asyncio
async def test_client_disconnect_closes_the_upstream_stream():
    """A disconnect must release the httpx response, not wait for GC."""
    closed = {"value": False}

    async def source():
        try:
            yield CONTENT_CHUNK
            await asyncio.sleep(3600)  # pragma: no cover - aborted by aclose()
        finally:
            closed["value"] = True

    stream = audited_sse_stream(source(), lambda _r: None)
    assert (await stream.__anext__()).startswith(b"data:")
    await stream.aclose()

    assert closed["value"] is True


# --------------------------------------------------------------------------- #
# Terminator ordering: exactly one [DONE], always last, whatever the provider does
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_crlf_framed_stream_passes_through_byte_identically():
    """SSE allows CRLF boundaries; they must not be mistaken for a dead stream."""
    crlf = [
        chunk.replace(b"\n\n", b"\r\n\r\n")
        for chunk in (CONTENT_CHUNK, FINISH_CHUNK, DONE_CHUNK)
    ]

    body, result = await _relay(crlf)

    assert body == b"".join(crlf)
    assert b"Hello" in body
    assert _finish_reasons(body) == ["stop"]
    assert result["completed"] is True
    assert result["truncated"] is False


@pytest.mark.asyncio
async def test_event_batching_content_with_the_terminator_keeps_the_content():
    batched = (
        b'data: {"id": "gen-1", "model": "m", "choices": [{"index": 0, '
        b'"delta": {"content": "Hello"}, "finish_reason": null}]}\n'
        b"data: [DONE]\n\n"
    )

    body, result = await _relay([batched])

    assert b"Hello" in body
    assert _finish_reasons(body) == ["length"]
    assert [event for event in _events(body) if event.strip() == "data: [DONE]"] == [
        "data: [DONE]"
    ]
    assert result["truncated"] is True


@pytest.mark.asyncio
async def test_duplicate_terminator_is_reduced_to_one():
    body, result = await _relay([CONTENT_CHUNK, FINISH_CHUNK, DONE_CHUNK, DONE_CHUNK])

    assert [event for event in _events(body) if event.strip() == "data: [DONE]"] == [
        "data: [DONE]"
    ]
    assert result["completed"] is True


@pytest.mark.asyncio
async def test_early_terminator_still_ends_with_one_done():
    """A [DONE] that arrives before finish_reason must not leave the stream open."""
    usage = b'data: {"choices": [], "usage": {"total_tokens": 5}}\n\n'

    body, result = await _relay([CONTENT_CHUNK, DONE_CHUNK, usage, FINISH_CHUNK])

    assert [event for event in _events(body) if event.strip() == "data: [DONE]"] == [
        "data: [DONE]"
    ]
    assert _finish_reasons(body) == ["stop"]
    assert body.endswith(DONE_CHUNK)
    assert result["completed"] is True


@pytest.mark.asyncio
async def test_provider_reset_after_final_chunk_is_completed_not_truncated():
    """A reset after a delivered finish_reason is a complete answer with a noisy EOF."""

    async def source():
        yield CONTENT_CHUNK
        yield FINISH_CHUNK
        raise ConnectionResetError("peer reset")

    body, result = await _drain(source())

    assert body.endswith(DONE_CHUNK)
    assert [event for event in _events(body) if event.strip() == "data: [DONE]"] == [
        "data: [DONE]"
    ]
    assert result["truncated"] is False
    assert result["completed"] is True
    assert "ConnectionResetError" in (result["error"] or "")


@pytest.mark.asyncio
async def test_nothing_is_emitted_after_the_terminator():
    body, result = await _relay(
        [CONTENT_CHUNK, FINISH_CHUNK, DONE_CHUNK, b'data: {"choices": []}']
    )

    assert body.endswith(DONE_CHUNK)
    assert _events(body)[-1].strip() == "data: [DONE]"
    assert result["completed"] is True


def test_truncation_marker_names_the_cause():
    """The marker distinguishes provider EOF, provider error and proxy degradation."""
    from apps.free_llm_proxy import streaming

    state = streaming._new_state()
    causes = [
        streaming._terminal_chunk(state, streaming.TRUNCATION_UPSTREAM_EOF),
        streaming._terminal_chunk(state, streaming.TRUNCATION_UPSTREAM_ERROR),
        streaming._terminal_chunk(state, streaming.TRUNCATION_DEGRADED),
    ]

    markers = [
        json.loads(chunk[5:].strip())[streaming.TRUNCATION_MARKER_KEY]
        for chunk in causes
    ]
    assert markers == [
        streaming.TRUNCATION_UPSTREAM_EOF,
        streaming.TRUNCATION_UPSTREAM_ERROR,
        streaming.TRUNCATION_DEGRADED,
    ]


def _audit_db(monkeypatch) -> AuditDB:
    from apps.free_llm_proxy import server

    db = AuditDB(db_path=":memory:")
    monkeypatch.setattr(server, "audit_db", db)
    return db


def test_provider_dying_before_first_token_is_failed_over(client, monkeypatch):
    """A role-only chunk followed by EOF must retry the next provider."""
    from apps.free_llm_proxy import server

    db = _audit_db(monkeypatch)
    chain = [("kilo", provider_cfg("kilo")), ("nvidia", provider_cfg("nvidia"))]
    install_chain(monkeypatch, chain)
    install_catalog(monkeypatch, {"kilo": ["kilo-auto/free"], "nvidia": ["nemotron"]})

    calls: list[str] = []

    async def mock_execute(provider_cfg, payload, stream=False):
        calls.append(provider_cfg.get("name"))

        async def dead():
            yield ROLE_ONLY_CHUNK

        async def healthy():
            yield CONTENT_CHUNK
            yield FINISH_CHUNK
            yield DONE_CHUNK

        return (200, dead(), {}) if len(calls) == 1 else (200, healthy(), {})

    monkeypatch.setattr(server, "execute_completion", mock_execute)

    response = client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={
            "model": "auto-go",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert len(calls) == 2
    assert "Hello" in response.text
    assert _finish_reasons(response.content) == ["stop"]
    call = db.get_metrics()["recent_calls"][0]
    assert call["stream_completed"] == 1
    assert "before first token" in (call["failover_chain"] or "")


def test_provider_raising_before_first_token_is_failed_over(client, monkeypatch):
    """A connection reset before any content must retry, not truncate."""
    from apps.free_llm_proxy import server

    db = _audit_db(monkeypatch)
    install_chain(
        monkeypatch,
        [("kilo", provider_cfg("kilo")), ("nvidia", provider_cfg("nvidia"))],
    )
    install_catalog(monkeypatch, {"kilo": ["kilo-auto/free"], "nvidia": ["nemotron"]})

    calls: list[str] = []

    async def mock_execute(provider_cfg, payload, stream=False):
        calls.append(provider_cfg.get("name"))

        async def reset():
            raise ConnectionResetError("peer reset")
            yield b""  # pragma: no cover - makes this an async generator

        async def healthy():
            yield CONTENT_CHUNK
            yield FINISH_CHUNK
            yield DONE_CHUNK

        return (200, reset(), {}) if len(calls) == 1 else (200, healthy(), {})

    monkeypatch.setattr(server, "execute_completion", mock_execute)

    response = client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={
            "model": "auto-go",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert len(calls) == 2
    assert "Hello" in response.text
    assert db.get_metrics()["recent_calls"][0]["stream_completed"] == 1


def test_all_providers_dying_before_first_token_returns_502(client, monkeypatch):
    """When every candidate dies before the first token, fail closed, not open."""
    from apps.free_llm_proxy import server

    _audit_db(monkeypatch)
    install_chain(monkeypatch, [("kilo", provider_cfg("kilo"))])
    install_catalog(monkeypatch, {"kilo": ["kilo-auto/free"]})

    async def mock_execute(provider_cfg, payload, stream=False):
        async def dead():
            yield ROLE_ONLY_CHUNK

        return 200, dead(), {}

    monkeypatch.setattr(server, "execute_completion", mock_execute)

    response = client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={
            "model": "auto-go",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )

    assert response.status_code == 502
    assert "before first token" in json.dumps(response.json())


# --------------------------------------------------------------------------- #
# Telemetry + circuit breaker
# --------------------------------------------------------------------------- #


def test_midstream_truncation_is_logged_as_incomplete(client, monkeypatch):
    """A truncated relay is an incomplete stream, not a success."""
    from apps.free_llm_proxy import server

    db = _audit_db(monkeypatch)
    install_chain(monkeypatch, [("kilo", provider_cfg("kilo"))])
    install_catalog(monkeypatch, {"kilo": ["kilo-auto/free"]})

    async def mock_execute(provider_cfg, payload, stream=False):
        async def chunks():
            yield CONTENT_CHUNK
            yield ROLE_ONLY_CHUNK

        return 200, chunks(), {}

    monkeypatch.setattr(server, "execute_completion", mock_execute)

    client.post(
        "/v1/chat/completions",
        headers=HEADERS,
        json={
            "model": "auto-go",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )

    metric = db.get_metrics()
    assert metric["incomplete_streams"] == 1
    call = metric["recent_calls"][0]
    assert call["stream_completed"] == 0
    assert "truncated" in (call["error_message"] or "").lower()


def test_stream_failure_needs_two_strikes_to_cool_a_provider():
    """One truncation is noise; two in a row take the provider out of rotation."""
    breaker = CircuitBreaker(default_cooldown_seconds=60)

    breaker.record_stream_failure("kilo")
    assert breaker.is_healthy("kilo")

    # A clean stream between two truncations means the provider is not broken.
    breaker.record_success("kilo")
    breaker.record_stream_failure("kilo")
    assert breaker.is_healthy("kilo")

    breaker.record_stream_failure("kilo")
    assert not breaker.is_healthy("kilo")


def test_truncated_stream_counts_against_the_provider(client, monkeypatch):
    """The dispatch-time success reset must not hide a truncated stream."""
    from apps.free_llm_proxy import server

    _audit_db(monkeypatch)
    install_chain(monkeypatch, [("kilo", provider_cfg("kilo"))])
    install_catalog(monkeypatch, {"kilo": ["kilo-auto/free"]})

    async def mock_execute(provider_cfg, payload, stream=False):
        async def chunks():
            yield CONTENT_CHUNK

        return 200, chunks(), {}

    monkeypatch.setattr(server, "execute_completion", mock_execute)

    for _ in range(2):
        client.post(
            "/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "auto-go",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        )

    assert server.circuit_breaker.is_healthy("kilo") is False


# --------------------------------------------------------------------------- #
# Catalog
# --------------------------------------------------------------------------- #


def test_retired_provider_is_absent_from_the_catalog():
    """OVHcloud's demo endpoint truncates a third of pi's streams: it is retired."""
    providers = load_providers_config()["providers"]
    assert "ovhcloud" not in providers
