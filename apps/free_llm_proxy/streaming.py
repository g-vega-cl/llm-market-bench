"""SSE stream auditing: capture usage without touching the bytes sent to clients."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterable, AsyncIterator, Callable
from typing import Any

logger = logging.getLogger("free_llm_proxy.streaming")

MAX_PARSE_BUFFER_BYTES = 1_048_576


def _parse_usage(payload: bytes) -> dict[str, Any] | None:
    """Return a usage object from a single SSE data payload, if present."""
    if not payload or payload == b"[DONE]":
        return None
    try:
        obj = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    usage = obj.get("usage")
    return usage if isinstance(usage, dict) else None


def _process_line(line: bytes, state: dict[str, Any]) -> None:
    line = line.rstrip(b"\r")
    if not line.startswith(b"data:"):
        return
    payload = line[5:].strip()
    if payload == b"[DONE]":
        state["saw_done"] = True
        return
    usage = _parse_usage(payload)
    if usage is not None:
        state["usage"] = usage


def _as_bytes(chunk: Any) -> bytes | None:
    if isinstance(chunk, bytes):
        return chunk
    if isinstance(chunk, (bytearray, memoryview)):
        return bytes(chunk)
    if isinstance(chunk, str):
        return chunk.encode("utf-8")
    return None


async def audited_sse_stream(
    source: AsyncIterable[Any],
    on_complete: Callable[[dict[str, Any]], None],
    *,
    started_at: float | None = None,
    max_buffer_bytes: int | None = None,
) -> AsyncIterator[Any]:
    """Yield SSE chunks unchanged while collecting the final usage object.

    The parser is observational only: it reads a copy of each chunk, never
    re-encodes or delays the chunk, and stops parsing (while still streaming)
    if a single SSE line grows beyond the bounded buffer.

    ``on_complete`` is called exactly once after the stream ends, errors, or is
    cancelled. It is synchronous because the audit DB write is synchronous and
    must also be safe during generator cleanup.
    """
    start = started_at if started_at is not None else time.perf_counter()
    limit = max_buffer_bytes if max_buffer_bytes is not None else MAX_PARSE_BUFFER_BYTES
    state: dict[str, Any] = {"saw_done": False, "usage": None}
    buffer = b""
    parse_enabled = True
    first_chunk_at: float | None = None
    error: str | None = None
    cancelled = False

    try:
        async for chunk in source:
            if first_chunk_at is None:
                first_chunk_at = time.perf_counter()

            raw = _as_bytes(chunk)
            if raw is not None and parse_enabled:
                if len(buffer) + len(raw) > limit:
                    parse_enabled = False
                    buffer = b""
                else:
                    buffer += raw
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        _process_line(line, state)

            yield chunk
    except (GeneratorExit, asyncio.CancelledError):
        cancelled = True
        error = "client disconnected before stream completion"
        raise
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if parse_enabled and buffer:
            _process_line(buffer, state)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        ttft_ms = (
            round((first_chunk_at - start) * 1000, 1)
            if first_chunk_at is not None
            else 0.0
        )
        completed = bool(state["saw_done"] or (error is None and not cancelled))

        try:
            on_complete(
                {
                    "usage": state["usage"],
                    "completed": completed,
                    "ttft_ms": ttft_ms,
                    "duration_ms": duration_ms,
                    "error": error,
                }
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist stream audit telemetry")
