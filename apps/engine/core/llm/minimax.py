"""MiniMax LLM client for market sentiment analysis."""

import json
import logging
import time
from typing import Any

import httpx

from core import config

logger = logging.getLogger("engine")


class MiniMaxClient:
    """Async client for MiniMax Text Chat API.

    API Docs: https://platform.minimax.io/docs/llms.txt
    Endpoint: POST https://api.minimax.io/v1/text/chatcompletion_v2
    """

    BASE_URL = "https://api.minimax.io/v1/text/chatcompletion_v2"
    TIMEOUT = 120.0

    def __init__(self, api_key: str | None = None):
        """Initialize MiniMax client.

        Args:
            api_key: MiniMax API key. Defaults to MINIMAX_API_KEY from config.
        """
        self.api_key = api_key or config.MINIMAX_API_KEY
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY is required")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.TIMEOUT,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_completion_tokens: int = 4096,
        stream: bool = False,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request to MiniMax.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model ID (defaults to MINIMAX_MODEL from config).
            temperature: Randomness (0, 1].
            max_completion_tokens: Max response length.
            stream: Whether to use streaming.

        Returns:
            Parsed JSON response from MiniMax API.

        Raises:
            httpx.HTTPStatusError: On API errors.
            ValueError: On malformed responses.
        """
        client = await self._get_client()
        if model is None:
            model = config.MINIMAX_MODEL

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_completion_tokens,
            "max_completion_tokens": max_completion_tokens,
            "stream": stream,
        }
        if response_format:
            payload["response_format"] = response_format

        start_time = time.time()
        try:
            response = await client.post(self.BASE_URL, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            try:
                error_body = e.response.json()
            except Exception:
                error_body = e.response.text
            logger.error(
                "MiniMax API HTTP error %d: %s",
                e.response.status_code,
                error_body,
            )
            raise e

        elapsed_ms = int((time.time() - start_time) * 1000)

        data = response.json()

        # Check for MiniMax specific API error in base_resp or error
        if "base_resp" in data:
            base_resp = data["base_resp"]
            status_code = base_resp.get("status_code")
            status_msg = base_resp.get("status_msg")
            if status_code is not None and status_code != 0:
                err_msg = f"MiniMax API error in base_resp: status_code={status_code}, status_msg='{status_msg}'"
                logger.error(err_msg)
                raise ValueError(err_msg)

        if "error" in data:
            error_data = data["error"]
            err_msg = f"MiniMax API error: {error_data}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        # Extract usage info if available
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")

        choices = data.get("choices", [])
        if not choices:
            logger.warning(
                "MiniMax API returned response with empty choices. Full response: %s",
                data,
            )

        return {
            "content": choices[0].get("message", {}).get("content", "") if choices else "",
            "model": data.get("model"),
            "finish_reason": choices[0].get("finish_reason") if choices else None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            "processing_time_ms": elapsed_ms,
            "raw_response": data,
        }

    async def chat_with_json_response(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_completion_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a chat request and parse JSON from the response content.

        This method extracts the JSON from the model's text response,
        making it easier to get structured data without requiring
        function calling / structured output modes.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model ID (defaults to MINIMAX_MODEL from config).
            temperature: Lower temperature for more deterministic output.
            max_completion_tokens: Max response length.

        Returns:
            Parsed JSON as a dictionary.

        Raises:
            ValueError: If response content is not valid JSON.
        """
        response = await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            response_format={"type": "json_object"},
        )

        content = response["content"].strip()

        # Try to extract JSON from markdown code blocks if present
        if content.startswith("```"):
            # Remove markdown code block syntax
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])  # Remove first (```json) and last (```) lines

        try:
            parsed = json.loads(content, strict=False)
            return parsed
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from MiniMax response: %s\nContent: %s", e, content[:500])
            raise ValueError(f"Invalid JSON response from MiniMax: {e}") from e

    async def __aenter__(self) -> "MiniMaxClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
