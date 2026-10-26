"""Async HTTP client for dispatching non-streaming and SSE streaming chat completions."""

from collections.abc import AsyncGenerator
from typing import Any
import httpx


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
        client = httpx.AsyncClient(timeout=60.0)
        should_close = True

    try:
        if not stream:
            resp = await client.post(url, headers=headers, json=payload)
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
            req = client.build_request("POST", url, headers=headers, json=payload)
            resp = await client.send(req, stream=True)
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
