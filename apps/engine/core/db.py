"""Supabase database client and operations.

This module provides functions for interacting with the Supabase database,
including client initialization and data operations.
"""

from typing import Any

from supabase import Client, create_client

from .config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL, logger


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
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


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
