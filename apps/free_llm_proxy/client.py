"""Async HTTP client for dispatching non-streaming and SSE streaming chat completions."""

from collections.abc import AsyncGenerator
from typing import Any

import httpx

from apps.free_llm_proxy import config

# Used only when the wall-clock cap is disabled (<= 0): a generous read window.
_FALLBACK_TOTAL_TIMEOUT = 300.0


def build_timeout(connect: float = 3.0) -> httpx.Timeout:
    """Returns the per-attempt httpx timeout derived from the configured cap.

    The read window must not be a second, tighter cap: a hardcoded 60s here would
    make `CLOUD_REQUEST_TIMEOUT_SECONDS` unreachable and surface long reasoning
    passes as connection errors instead of `504 timeout_error`.
    """
    total = config.CLOUD_REQUEST_TIMEOUT_SECONDS
    if total <= 0:
        total = _FALLBACK_TOTAL_TIMEOUT
    return httpx.Timeout(total, connect=connect)


def build_request_headers(provider_cfg: dict) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = provider_cfg.get("api_key")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Merge optional provider-specific extra headers (e.g. OpenRouter referer)
    extra = provider_cfg.get("extra_headers", {})
    if extra:
        headers.update(extra)
    return headers


async def execute_completion(
    provider_cfg: dict,
    payload: dict[str, Any],
    stream: bool = False,
    client: httpx.AsyncClient | None = None,
) -> tuple[int, Any, dict[str, str]]:
    """Dispatches a chat completion request to the given provider.

    Returns:
        tuple of (status_code, response_payload_or_generator, response_headers)
    """
    base_url = provider_cfg["base_url"].rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = build_request_headers(provider_cfg)

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=build_timeout())
        should_close = True

    try:
        if not stream:
            try:
                resp = await client.post(url, headers=headers, json=payload)
            except httpx.TimeoutException as exc:
                return (
                    504,
                    {
                        "error": {
                            "message": f"Provider {base_url} timed out: {exc}",
                            "type": "timeout_error",
                        }
                    },
                    {},
                )
            except httpx.RequestError as exc:
                return (
                    503,
                    {
                        "error": {
                            "message": f"Provider connection error: {exc}",
                            "type": "connection_error",
                        }
                    },
                    {},
                )
            resp_headers = dict(resp.headers)
            try:
                body = resp.json()
            except Exception:
                body = {
                    "error": {"message": resp.text, "status_code": resp.status_code}
                }
            return resp.status_code, body, resp_headers

        else:
            # For streaming, probe the connection first to catch initial 429/5xx before yielding chunks
            try:
                req = client.build_request("POST", url, headers=headers, json=payload)
                resp = await client.send(req, stream=True)
            except httpx.TimeoutException as exc:
                if should_close:
                    await client.aclose()
                return (
                    504,
                    {
                        "error": {
                            "message": f"Provider {base_url} timed out: {exc}",
                            "type": "timeout_error",
                        }
                    },
                    {},
                )
            except httpx.RequestError as exc:
                if should_close:
                    await client.aclose()
                return (
                    503,
                    {
                        "error": {
                            "message": f"Provider connection error: {exc}",
                            "type": "connection_error",
                        }
                    },
                    {},
                )
            resp_headers = dict(resp.headers)

            if resp.status_code != 200:
                await resp.aread()
                try:
                    err_body = resp.json()
                except Exception:
                    err_body = {
                        "error": {"message": resp.text, "status_code": resp.status_code}
                    }
                await resp.aclose()
                if should_close:
                    await client.aclose()
                return resp.status_code, err_body, resp_headers

            async def sse_generator() -> AsyncGenerator[bytes, None]:
                try:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
                finally:
                    await resp.aclose()
                    if should_close:
                        await client.aclose()

            return 200, sse_generator(), resp_headers

    finally:
        if should_close and not stream:
            await client.aclose()
