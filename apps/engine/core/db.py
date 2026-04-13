import time
import httpx
from typing import Any, Callable, TypeVar

from supabase import Client, create_client, ClientOptions

from .config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL, logger

T = TypeVar("T")

SUPABASE_RETRIES = 3


def get_supabase_client() -> Client:
    """Initialize and return a Supabase client using the service role key.

    Returns:
        A configured Supabase client instance.

    Raises:
        ValueError: If Supabase configuration is missing.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        error_msg = (
            "Supabase configuration missing: ensure SUPABASE_PROJECT_URL "
            "and SUPABASE_SERVICE_ROLE_KEY are set."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Configure httpx client to avoid deprecation warnings in supabase-py
    # by moving timeout and verify settings into the http_client itself.
    http_client = httpx.Client(
        timeout=httpx.Timeout(10.0, connect=5.0),
        verify=True
    )
    
    options = ClientOptions(
        httpx_client=http_client,
        postgrest_client_timeout=10.0,
        storage_client_timeout=10
    )
    
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, options=options)


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


def with_retry(operation: Callable[[], T], operation_name: str = "operation") -> T:
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
                logger.error(f"{operation_name} failed with non-transient error: {exc}")
                raise
            
            if attempt < SUPABASE_RETRIES:
                wait_time = 2 ** (attempt - 1)
                logger.warning(
                    f"{operation_name} failed (attempt {attempt}/{SUPABASE_RETRIES}), "
                    f"retrying in {wait_time}s. Error: {exc}"
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"{operation_name} failed after {SUPABASE_RETRIES} attempts. "
                    f"Last error: {exc}"
                )
    
    raise last_exception


def upsert_newsletter_snapshot(
    client: Client,
    data: dict[str, Any]
) -> dict[str, Any]:
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
        response = client.table("newsletter_snapshots").upsert(
            payload,
            on_conflict="date,source_id"
        ).execute()

        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to upsert snapshot for {data.get('source_id')}: {e}")
        raise
