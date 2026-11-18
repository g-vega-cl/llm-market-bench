"""SSE stream auditing, terminal-chunk guarantees, and first-token priming.

Two jobs:

1. ``audited_sse_stream`` relays upstream bytes while collecting usage telemetry,
   and guarantees every response ends with a chunk carrying a non-null
   ``finish_reason`` followed by exactly one ``data: [DONE]`` — with nothing after
   it. Providers that close the connection after the first chunk, that end a stream
   with ``[DONE]`` alone, that batch content with the terminator, or that reset
   after their final chunk otherwise leave strict OpenAI clients (pi, the OpenAI
   SDKs) raising "Stream ended without finish_reason" — a failure the proxy cannot
   fail over from once the 200 headers are gone.

2. ``prime_sse_stream`` reads the head of an upstream stream so the router can fail
   over *before* committing to a provider: a stream that dies before the first
   content delta is indistinguishable from a dead provider, and the caller still
   owns the response at that point.

The relay is event-framed by :class:`SSEScanner` (LF, CRLF and CR boundaries) and
never writes bytes it has not framed. Terminality is decided from parsed ``data:``
payloads and from what has actually been *emitted*, so ordering quirks — split
terminators, ``data:[DONE]``, quoted terminators, duplicate, early or missing
terminators — cannot corrupt a stream or leave it unterminated.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import AsyncIterable, AsyncIterator, Callable
from typing import Any

logger = logging.getLogger("free_llm_proxy.streaming")

MAX_PARSE_BUFFER_BYTES = 1_048_576
PRIME_MAX_CHUNKS = 8
PRIME_MAX_BYTES = 65_536

#: Standard OpenAI finish_reason for incomplete output. Used when a stream stops
#: early so strict clients treat it as truncated output rather than as a fault.
TRUNCATION_FINISH_REASON = "length"
#: Non-standard marker on the synthesized chunk so a caller can tell a provider
#: death (or a proxy degradation) from a real ``max_tokens`` cut.
TRUNCATION_MARKER_KEY = "x_proxy_truncated"
TRUNCATION_UPSTREAM_EOF = "upstream_eof"
TRUNCATION_UPSTREAM_ERROR = "upstream_error"
TRUNCATION_DEGRADED = "degraded"

DONE_FRAME = b"data: [DONE]\n\n"
_DONE_PAYLOAD = b"[DONE]"
_FRAME_SEPARATOR = b"\n\n"
_EVENT_BOUNDARIES = (b"\r\n\r\n", b"\n\n", b"\r\r")
_LINE_SPLIT = re.compile(rb"\r\n|\r|\n")

_CONTENT_DELTA_KEYS = (
    "content",
    "reasoning",
    "reasoning_content",
    "tool_calls",
    "function_call",
)


class SSEScanner:
    """Incremental SSE framing: arbitrary byte chunks in, whole events out.

    An event is everything up to and including its terminating blank line (LF, CRLF
    or CR), so concatenating every event reproduces the upstream bytes exactly.
    Unterminated bytes stay in :attr:`tail` and are never emitted mid-stream, which
    is what keeps a synthesized terminal chunk from being fused onto a half-written
    event.

    If a single event exceeds ``max_event_bytes`` the scanner degrades to raw
    pass-through and says so (``degraded``), so the caller can record an explained
    failure instead of silently dropping the terminal-chunk guarantee.
    """

    def __init__(self, max_event_bytes: int = MAX_PARSE_BUFFER_BYTES) -> None:
        self._max_event_bytes = max_event_bytes
        self._buffer = b""
        self.degraded = False
        self.oversized_event_bytes = 0

    @property
    def tail(self) -> bytes:
        """Bytes of an unterminated trailing event, if any."""
        return self._buffer

    def feed(self, raw: bytes) -> list[bytes]:
        if self.degraded:
            return [raw] if raw else []
        self._buffer += raw
        events: list[bytes] = []
        while True:
            boundary = _next_boundary(self._buffer)
            if boundary is None:
                break
            index, span = boundary
            end = index + span
            events.append(self._buffer[:end])
            self._buffer = self._buffer[end:]
        if len(self._buffer) > self._max_event_bytes:
            self.degraded = True
            self.oversized_event_bytes = len(self._buffer)
            events.append(self._buffer)
            self._buffer = b""
        return events


def _next_boundary(buffer: bytes) -> tuple[int, int] | None:
    """Earliest SSE event boundary in ``buffer`` as ``(index, separator length)``."""
    found: tuple[int, int] | None = None
    for separator in _EVENT_BOUNDARIES:
        index = buffer.find(separator)
        if index != -1 and (found is None or index < found[0]):
            found = (index, len(separator))
    return found


def _event_lines(event: bytes) -> list[bytes]:
    """Non-empty lines of an event, split on any spec-legal line ending."""
    return [line for line in _LINE_SPLIT.split(event) if line.strip()]


def _as_bytes(chunk: Any) -> bytes | None:
    if isinstance(chunk, bytes):
        return chunk
    if isinstance(chunk, (bytearray, memoryview)):
        return bytes(chunk)
    if isinstance(chunk, str):
        return chunk.encode("utf-8")
    return None


def _parse_payload(payload: bytes) -> dict[str, Any] | None:
    """Return a decoded SSE data payload, or None when it is not a JSON object."""
    if not payload or payload == _DONE_PAYLOAD:
        return None
    try:
        obj = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _payload_from_line(line: bytes) -> bytes:
    line = line.strip()
    if not line.startswith(b"data:"):
        return b""
    return line[5:].strip()


def _delta_has_content(delta: Any) -> bool:
    """True once the provider has emitted anything a client can show or act on."""
    if not isinstance(delta, dict):
        return False
    return any(delta.get(key) for key in _CONTENT_DELTA_KEYS)


def _new_state() -> dict[str, Any]:
    return {
        "saw_content": False,
        "saw_tool_call": False,
        "saw_finish_reason": False,
        "finish_reason": None,
        "usage": None,
        "chunk_id": None,
        "model": None,
    }


def _process_line(line: bytes, state: dict[str, Any]) -> None:
    obj = _parse_payload(_payload_from_line(line))
    if obj is None:
        return
    usage = obj.get("usage")
    if isinstance(usage, dict):
        state["usage"] = usage
    if isinstance(obj.get("id"), str):
        state["chunk_id"] = obj["id"]
    if isinstance(obj.get("model"), str):
        state["model"] = obj["model"]
    for choice in obj.get("choices") or []:
        if not isinstance(choice, dict):
            continue
        delta = choice.get("delta")
        if choice.get("finish_reason"):
            state["saw_finish_reason"] = True
            state["finish_reason"] = choice["finish_reason"]
        if _delta_has_content(delta):
            state["saw_content"] = True
        if isinstance(delta, dict) and (
            delta.get("tool_calls") or delta.get("function_call")
        ):
            state["saw_tool_call"] = True


def _process_event(event: bytes, state: dict[str, Any]) -> None:
    for line in _event_lines(event):
        _process_line(line, state)


def _event_produces(event: bytes) -> bool:
    """True when an event carries content or a terminal marker (priming signal)."""
    for line in _event_lines(event):
        payload = _payload_from_line(line)
        if payload == _DONE_PAYLOAD:
            return True
        obj = _parse_payload(payload)
        if obj is None:
            continue
        for choice in obj.get("choices") or []:
            if isinstance(choice, dict) and (
                choice.get("finish_reason") or _delta_has_content(choice.get("delta"))
            ):
                return True
    return False


def _terminal_chunk(state: dict[str, Any], cause: str) -> bytes:
    """The synthetic event that closes a stream the provider failed to close."""
    payload = {
        "id": state.get("chunk_id") or "chatcmpl-truncated",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": state.get("model") or "unknown",
        "choices": [
            {"index": 0, "delta": {}, "finish_reason": TRUNCATION_FINISH_REASON}
        ],
        TRUNCATION_MARKER_KEY: cause,
    }
    return (
        b"data: "
        + json.dumps(payload, separators=(",", ":")).encode("utf-8")
        + _FRAME_SEPARATOR
    )


def _new_flags() -> dict[str, Any]:
    return {"done_emitted": False, "truncated": False, "failed": False, "error": None}


def _route_event(
    event: bytes, state: dict[str, Any], flags: dict[str, Any]
) -> list[bytes]:
    """Frames to forward for one event, enforcing exactly-one-terminator rules."""
    lines = _event_lines(event)
    payloads = [_payload_from_line(line) for line in lines]

    if _DONE_PAYLOAD not in payloads:
        _process_event(event, state)
        return [event]

    # Content may be batched with the terminator in a single event: parse the rest.
    others = [
        line
        for line, payload in zip(lines, payloads, strict=False)
        if payload != _DONE_PAYLOAD
    ]
    for line in others:
        _process_line(line, state)
    if flags["done_emitted"]:
        return []  # duplicate terminator: keep exactly one
    if state["saw_finish_reason"]:
        flags["done_emitted"] = True
        return [event]
    # Without a finish_reason the terminator is withheld and superseded by the
    # close-out repair; any content batched with it is still forwarded.
    return [b"\n".join(others) + _FRAME_SEPARATOR] if others else []


def _close_out(
    scanner: SSEScanner, state: dict[str, Any], flags: dict[str, Any]
) -> list[bytes]:
    """Emit the terminator: exactly one ``[DONE]``, and nothing after it.

    Mutates ``flags`` (``done_emitted``, ``truncated``, ``error``) so telemetry
    reflects what was actually written rather than what was merely observed.
    """
    events: list[bytes] = []

    tail = scanner.tail
    if tail and not flags["done_emitted"] and not scanner.degraded:
        # An unterminated final event is forwarded only when it parses, and it is
        # always closed so nothing can be fused onto it. Unparseable fragments are
        # dropped: re-emitting them would corrupt the stream.
        if _parse_payload(_payload_from_line(tail)) is not None:
            _process_event(tail, state)
            events.append(tail + _FRAME_SEPARATOR)

    if flags["done_emitted"]:
        return events  # a terminator is already out; nothing may follow it

    if scanner.degraded:
        flags["truncated"] = True
        flags["error"] = flags["error"] or (
            "stream degraded: SSE event exceeded "
            f"{scanner.oversized_event_bytes} bytes; "
            "terminal-chunk guarantee unavailable"
        )
        events.extend([_terminal_chunk(state, TRUNCATION_DEGRADED), DONE_FRAME])
    elif not state["saw_finish_reason"]:
        flags["truncated"] = True
        cause = (
            TRUNCATION_UPSTREAM_ERROR if flags["failed"] else TRUNCATION_UPSTREAM_EOF
        )
        events.extend([_terminal_chunk(state, cause), DONE_FRAME])
    else:
        events.append(DONE_FRAME)

    flags["done_emitted"] = True
    return events


async def audited_sse_stream(
    source: AsyncIterable[Any],
    on_complete: Callable[[dict[str, Any]], None],
    *,
    started_at: float | None = None,
    max_buffer_bytes: int | None = None,
) -> AsyncIterator[Any]:
    """Relay SSE events while enforcing a terminal chunk and recording telemetry.

    A well-formed stream is byte-identical. A stream that ends without a
    ``finish_reason`` gains a synthetic ``finish_reason: "length"`` event plus
    ``data: [DONE]`` and is reported ``truncated``; one that carried
    ``finish_reason`` but no terminator (or had content batched with the
    terminator) gets exactly one ``[DONE]``; duplicate or early terminators are
    normalised. ``on_complete`` is called exactly once, and the upstream source is
    closed on every exit path, including client disconnect.
    """
    start = started_at if started_at is not None else time.perf_counter()
    scanner = SSEScanner(max_buffer_bytes or MAX_PARSE_BUFFER_BYTES)
    state = _new_state()
    flags = _new_flags()
    first_chunk_at: float | None = None
    cancelled = False

    try:
        async for chunk in source:
            if first_chunk_at is None:
                first_chunk_at = time.perf_counter()

            raw = _as_bytes(chunk)
            if raw is None:
                yield chunk
                continue

            for event in scanner.feed(raw):
                if scanner.degraded:
                    # Framing is impossible, so no payload can be parsed — but the
                    # terminator can still be held back and replaced by the repair,
                    # which keeps "exactly one [DONE]" true even here.
                    if b"[DONE]" not in event:
                        yield event
                    continue

                for frame in _route_event(event, state, flags):
                    yield frame
    except (GeneratorExit, asyncio.CancelledError):
        cancelled = True
        flags["error"] = "client disconnected before stream completion"
        raise
    except Exception as exc:  # noqa: BLE001
        flags["failed"] = True
        flags["error"] = f"{type(exc).__name__}: {exc}"
        logger.exception("Upstream stream failed mid-flight")
    finally:
        await close_stream_source(source)

        if not cancelled:
            for event in _close_out(scanner, state, flags):
                yield event

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        ttft_ms = (
            round((first_chunk_at - start) * 1000, 1)
            if first_chunk_at is not None
            else 0.0
        )
        completed = bool(
            flags["done_emitted"]
            and state["saw_finish_reason"]
            and not flags["truncated"]
            and not cancelled
        )
        if flags["truncated"] and flags["error"] is None:
            flags["error"] = (
                "stream truncated: upstream ended without a finish_reason chunk"
            )

        try:
            on_complete(
                {
                    "usage": state["usage"],
                    "completed": completed,
                    "truncated": flags["truncated"],
                    "cancelled": cancelled,
                    "ttft_ms": ttft_ms,
                    "duration_ms": duration_ms,
                    "error": flags["error"],
                    "saw_content": state["saw_content"],
                    "saw_tool_call": state["saw_tool_call"],
                    "finish_reason": state["finish_reason"],
                }
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist stream audit telemetry")


async def prime_sse_stream(
    source: AsyncIterable[Any],
    *,
    max_chunks: int = PRIME_MAX_CHUNKS,
    max_bytes: int = PRIME_MAX_BYTES,
) -> tuple[list[Any], Any | None, bool]:
    """Read the head of an upstream stream before committing a 200 to the client.

    Returns ``(buffered_chunks, remaining_iterator, produced)``. ``produced`` is
    False only when the stream ended with nothing to relay — the signature of a
    provider that dies on connect, which the caller can still fail over from. Any
    unframed bytes count as produced: discarding a provider's answer to retry
    would be worse than relaying it with a repaired terminator.
    """
    iterator = source.__aiter__()
    scanner = SSEScanner()
    buffered: list[Any] = []
    total = 0

    while len(buffered) < max_chunks and total < max_bytes:
        try:
            chunk = await iterator.__anext__()
        except StopAsyncIteration:
            return buffered, None, bool(scanner.tail.strip())

        buffered.append(chunk)
        raw = _as_bytes(chunk) or b""
        total += len(raw)
        for event in scanner.feed(raw):
            if scanner.degraded or _event_produces(event):
                return buffered, iterator, True

    return buffered, iterator, True


async def close_stream_source(source: Any) -> None:
    """Close an upstream stream so its connection is released immediately."""
    aclose = getattr(source, "aclose", None)
    if aclose is None:
        return
    try:
        await aclose()
    except Exception:  # noqa: BLE001
        logger.debug(
            "Ignoring error while closing an abandoned upstream stream", exc_info=True
        )


def prefixed_stream(buffered: list[Any], upstream: Any | None) -> AsyncIterator[Any]:
    """Replays the primed head of a stream, then drains the same iterator.

    ``upstream`` is the already-advanced iterator from ``prime_sse_stream``; it is
    driven directly rather than re-entered through ``__aiter__`` so an iterable
    that mints a fresh iterator per call cannot replay and duplicate the head.
    """

    async def _relay() -> AsyncIterator[Any]:
        try:
            for chunk in buffered:
                yield chunk
            if upstream is None:
                return
            while True:
                try:
                    chunk = await upstream.__anext__()
                except StopAsyncIteration:
                    return
                yield chunk
        finally:
            if upstream is not None:
                await close_stream_source(upstream)

    return _relay()
