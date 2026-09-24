"""Tool execution audit logging module.

Records tool inputs, outputs, execution duration, and metadata to the local
analytical PostgreSQL archive database via PostgREST / Cloudflare Tunnel.
"""

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("engine.tool_audit")

# Maximum string length for tool outputs (1 MB safety ceiling)
MAX_PAYLOAD_BYTES = 1024 * 1024
DEFAULT_LOCAL_ARCHIVE_URL = "http://127.0.0.1:3001"
DEFAULT_REMOTE_ARCHIVE_URL = "https://benchify-archive-db.clvg.uk"
POSTGREST_TIMEOUT_SECONDS = 4.0


def get_archive_db_url() -> str:
    """Resolve the appropriate PostgREST archive endpoint URL.

    Checks:
    1. Explicit ARCHIVE_DB_URL environment variable.
    2. If running in CI (GITHUB_ACTIONS is set), defaults to the Cloudflare Tunnel URL.
    3. If running locally outside CI, defaults to localhost:3001.

    Returns:
        Base URL for the archive PostgREST service.
    """
    env_override = os.getenv("ARCHIVE_DB_URL")
    if env_override:
        return env_override.rstrip("/")

    if os.getenv("GITHUB_ACTIONS"):
        return DEFAULT_REMOTE_ARCHIVE_URL

    return DEFAULT_LOCAL_ARCHIVE_URL


async def record_tool_audit(
    tool_name: str,
    tool_args: dict[str, Any],
    tool_result: str,
    duration_ms: int,
    model_name: str = "",
    status: str = "success",
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Record a single tool execution to the analytical archive database.

    Defensive and non-blocking: errors or network timeouts log a warning
    and return False rather than raising an exception.

    Args:
        tool_name: Name of the executed tool.
        tool_args: Dictionary of arguments passed to the tool.
        tool_result: Text output returned by the tool.
        duration_ms: Wall-clock execution time in milliseconds.
        model_name: Name of the model initiating the tool call.
        status: 'success' or 'error'.
        metadata: Optional dictionary with additional execution context.

    Returns:
        True if the audit record was successfully written, False otherwise.
    """
    meta = dict(metadata) if metadata else {}

    raw_result = tool_result or ""
    if len(raw_result) > MAX_PAYLOAD_BYTES:
        truncated_result = raw_result[:MAX_PAYLOAD_BYTES]
        meta["truncated"] = True
        meta["original_bytes"] = len(raw_result)
    else:
        truncated_result = raw_result

    payload = {
        "tool_name": tool_name,
        "model_name": model_name or None,
        "tool_args": tool_args or {},
        "tool_result": truncated_result,
        "duration_ms": duration_ms,
        "status": status,
        "metadata": meta,
        "created_at": datetime.now(UTC).isoformat(),
    }

    base_url = get_archive_db_url()
    target_endpoint = f"{base_url}/tool_execution_logs"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(POSTGREST_TIMEOUT_SECONDS)) as client:
            resp = await client.post(target_endpoint, json=payload)
            if resp.status_code in (200, 201, 204):
                logger.info("Tool audit recorded for %s (%dms)", tool_name, duration_ms)
                return True
            logger.warning(
                "Tool audit rejected for %s (HTTP %d). Main pipeline continuing.",
                tool_name,
                resp.status_code,
            )
            return False
    except Exception as exc:
        logger.warning(
            "Tool audit recording skipped for %s (%s). Main pipeline continuing.",
            tool_name,
            exc.__class__.__name__,
        )
        return False


def async_record_tool_audit(
    tool_name: str,
    tool_args: dict[str, Any],
    tool_result: str,
    duration_ms: int,
    model_name: str = "",
    status: str = "success",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Schedule tool audit recording in the background without awaiting.

    Ensures that calling tools experiences zero added latency and any
    network issues cannot interrupt the main trading pipeline.
    """
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(
            record_tool_audit(
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=tool_result,
                duration_ms=duration_ms,
                model_name=model_name,
                status=status,
                metadata=metadata,
            )
        )

        def _on_done(t: asyncio.Task) -> None:
            if not t.cancelled() and t.exception():
                logger.warning(
                    "Background tool audit task for %s exited with %s. Main pipeline unaffected.",
                    tool_name,
                    t.exception().__class__.__name__,
                )

        task.add_done_callback(_on_done)
    except RuntimeError:
        # No running event loop in thread; drop safely
        logger.debug("No active event loop to schedule async tool audit for %s", tool_name)

