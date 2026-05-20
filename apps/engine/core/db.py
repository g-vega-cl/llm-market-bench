import asyncio
import inspect
import time
from collections.abc import Callable
from typing import Any, TypeVar

import httpx
from supabase import (
    AsyncClient,
    AsyncClientOptions,
    Client,
    ClientOptions,
    create_async_client,
    create_client,
)

from .config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL, logger

T = TypeVar("T")

SUPABASE_RETRIES = 3

_supabase_client: Client | None = None
_supabase_async_client: AsyncClient | None = None


def _validate_config():
    """Raise if Supabase configuration is missing."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        error_msg = "Supabase configuration missing: ensure SUPABASE_PROJECT_URL and SUPABASE_SERVICE_ROLE_KEY are set."
        logger.error(error_msg)
        raise ValueError(error_msg)


def _build_client_options():
    """Build ClientOptions with a configured httpx client."""
    http_client = httpx.Client(
        timeout=httpx.Timeout(10.0, connect=5.0),
        verify=True,
    )
    return ClientOptions(
        httpx_client=http_client,
        postgrest_client_timeout=10.0,
        storage_client_timeout=10,
    )


def _build_async_client_options():
    """Build AsyncClientOptions with a configured httpx async client."""
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        verify=True,
    )
    return AsyncClientOptions(
        httpx_client=http_client,
        postgrest_client_timeout=10.0,
        storage_client_timeout=10,
    )


def get_supabase_client() -> Client:
    """Return the shared sync Supabase client (singleton).

    Creates the client on first call and caches it for all subsequent
    calls. If ``create_client()`` ever becomes async in a future
    supabase-py version, this function detects it and resolves the
    coroutine.

    Returns:
        A configured sync Supabase client instance.

    Raises:
        ValueError: If Supabase configuration is missing.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    _validate_config()
    options = _build_client_options()
    result = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, options=options)

    if inspect.iscoroutine(result):
        logger.warning(
            "supabase.create_client returned a coroutine — "
            "resolving synchronously. Consider migrating to "
            "``await get_async_supabase_client()``."
        )
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(result)

    _supabase_client = result
    return _supabase_client


async def get_async_supabase_client() -> AsyncClient:
    """Return the shared async Supabase client (singleton).

    Creates the async client on first call and caches it. Prefer this
    over ``get_supabase_client()`` in async code paths — it uses the
    native async supabase client which is the direction of supabase-py.

    Returns:
        A configured async Supabase client instance.

    Raises:
        ValueError: If Supabase configuration is missing.
    """
    global _supabase_async_client
    if _supabase_async_client is not None:
        return _supabase_async_client

    _validate_config()
    options = _build_async_client_options()
    _supabase_async_client = await create_async_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, options=options)
    return _supabase_async_client


def is_transient_supabase_error(exc: Exception) -> bool:
    """Check if an exception is a transient Supabase error worth retrying."""
    error_str = str(exc).lower()

    transient_codes = {"502", "503", "504", "429"}
    for code in transient_codes:
        if code in error_str:
            return True

    transient_keywords = [
        "bad gateway",
        "service unavailable",
        "gateway timeout",
        "too many requests",
        "connection error",
        "connection reset",
        "network error",
        "timeout",
        "timed out",
        "could not connect",
        "connection refused",
    ]
    return any(kw in error_str for kw in transient_keywords)


def with_retry[T](operation: Callable[[], T], operation_name: str = "operation") -> T:
    """Execute a Supabase operation with retry logic and exponential backoff.

    Retries on transient errors (502, 503, 504, timeouts, connection errors).

    Args:
        operation: A callable that performs the Supabase operation.
        operation_name: Human-readable name for logging purposes.

    Returns:
        The result of the operation.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception = None

    for attempt in range(1, SUPABASE_RETRIES + 1):
        try:
            return operation()
        except Exception as exc:
            last_exception = exc

            if not is_transient_supabase_error(exc):
                logger.exception(f"{operation_name} failed with non-transient error")
                raise

            if attempt < SUPABASE_RETRIES:
                wait_time = 2 ** (attempt - 1)
                logger.warning(
                    f"{operation_name} failed (attempt {attempt}/{SUPABASE_RETRIES}), "
                    f"retrying in {wait_time}s. Error: {exc}"
                )
                time.sleep(wait_time)
            else:
                logger.exception(f"{operation_name} failed after {SUPABASE_RETRIES} attempts")

    raise last_exception


def upsert_newsletter_snapshot(client: Client, data: dict[str, Any]) -> dict[str, Any]:
    """Upsert a newsletter snapshot into the database.

    Uses the composite unique constraint (date, source_id) for idempotency,
    preventing duplicate entries if the job restarts.

    Args:
        client: The Supabase client instance.
        data: Dictionary containing newsletter snapshot fields:
            - source_id: Unique identifier for the newsletter chunk
            - chunk_hash: SHA-256 hash of the content
            - sender: Email sender address
            - subject: Email subject line
            - content: Processed email body text
            - date: ISO format datetime string

    Returns:
        The upserted row data as a dictionary.

    Raises:
        Exception: If the upsert operation fails.
    """
    payload = {
        "source_id": data["source_id"],
        "chunk_hash": data["chunk_hash"],
        "sender": data["sender"],
        "subject": data["subject"],
        "content": data["content"],
        "date": data["date"],
    }

    try:
        response = client.table("newsletter_snapshots").upsert(payload, on_conflict="date,source_id").execute()

        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to upsert snapshot for {data.get('source_id')}: {e}")
        raise
