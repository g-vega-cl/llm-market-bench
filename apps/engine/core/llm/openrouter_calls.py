"""OpenRouter decisions calls with local telemetry.

Seven engine sites post directly to OpenRouter's decisions alpha, ahead of any proxy.
They deliberately disagree on 4xx policy (some degrade to DISQUALIFIED, some raise), so
this wrapper only measures and records: it returns the response untouched and re-raises
transport errors after logging them.
"""

from __future__ import annotations

import inspect
import time
from typing import Any, Protocol

from core.llm import call_log

PROVIDER = "openrouter"
DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
ERROR_TEXT_LIMIT = 500


class _PostClient(Protocol):
    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any: ...


def _usage(body: Any) -> tuple[int, int, int]:
    """Extract token counts when the response carries them; decisions alpha often does not."""
    if not isinstance(body, dict):
        return 0, 0, 0
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return 0, 0, 0
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    return prompt_tokens, completion_tokens, total_tokens


def log_requests_call(
    *,
    purpose: str,
    model: str,
    preview: str | None,
    response: Any,
    latency_ms: float,
) -> None:
    """Record a synchronous ``requests`` chat completion (auto-wiki, wiki-lint).

    Those callers raise on their own terms right after this returns, so a failure is
    recorded and left to them.
    """
    ok = bool(getattr(response, "ok", False))
    status_code = int(getattr(response, "status_code", 0) or 0)
    body: Any = None
    if ok:
        try:
            body = response.json()
        except Exception:  # noqa: BLE001 - the caller validates the payload
            body = None
    prompt_tokens, completion_tokens, total_tokens = _usage(body)
    error_message = None
    if not ok:
        error_message = str(getattr(response, "text", "") or "")[:ERROR_TEXT_LIMIT] or f"HTTP {status_code}"

    call_log.log_call(
        requested_model=model,
        routed_provider=PROVIDER,
        routed_model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        status_code=status_code,
        error_message=error_message,
        purpose=purpose,
        prompt_preview=call_log.preview(preview),
        usage_available=total_tokens > 0,
        billing="paid",
    )


async def _json_body(resp: Any) -> Any:
    """Read a response body, tolerating the async ``json()`` mocks the tests use."""
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001 - a malformed body is the caller's problem to raise on
        return None
    if inspect.isawaitable(body):
        try:
            body = await body
        except Exception:  # noqa: BLE001 - same
            return None
    return body


async def post_decisions(
    client: _PostClient,
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    model: str,
    purpose: str,
    preview: str | None = None,
) -> Any:
    """POST a decisions payload, record the attempt, and hand the response back unchanged."""
    started = time.perf_counter()
    try:
        resp = await client.post(url, headers=headers, json=payload)
    except Exception as exc:
        call_log.log_call(
            requested_model=model,
            routed_provider=PROVIDER,
            routed_model=model,
            latency_ms=(time.perf_counter() - started) * 1000,
            status_code=0,
            error_message=f"{type(exc).__name__}: {exc}"[:ERROR_TEXT_LIMIT],
            purpose=purpose,
            prompt_preview=call_log.preview(preview),
            billing="paid",
        )
        raise

    latency_ms = (time.perf_counter() - started) * 1000
    status_code = int(getattr(resp, "status_code", 0) or 0)
    body: Any = None
    if status_code == 200:
        body = await _json_body(resp)
    prompt_tokens, completion_tokens, total_tokens = _usage(body)
    error_message = None
    if status_code != 200:
        error_message = str(getattr(resp, "text", "") or "")[:ERROR_TEXT_LIMIT] or f"HTTP {status_code}"

    call_log.log_call(
        requested_model=model,
        routed_provider=PROVIDER,
        routed_model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        status_code=status_code,
        error_message=error_message,
        purpose=purpose,
        prompt_preview=call_log.preview(preview),
        usage_available=total_tokens > 0,
        billing="paid",
    )
    return resp
