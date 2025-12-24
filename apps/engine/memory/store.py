"""Supabase pgvector store logic."""

import logging
from typing import Any, Optional
from supabase import Client
from core.db import get_supabase_client
from .embeddings import get_embedding

logger = logging.getLogger("engine")

def retrieve_context(query_text: str, limit: int = 3) -> str:
    """Retrieves relevant past events/reasoning from the vector store.

    Args:
        query_text: The text to search for (e.g., a news chunk).
        limit: Number of relevant snippets to return.

    Returns:
        A formatted string of relevant context found.
    """
    try:
        embedding = get_embedding(query_text)
        if not embedding:
            return ""

        client = get_supabase_client()
        
        # We use the rpc call to search_memories which we will define in the migration
        # or we can use the direct supabase-py interface if it supports vector search.
        # Currently, the best way with supabase-py is to use a Postgres function (RPC).
        # Let's assume we'll add a search_memories function to our migration.
        
        response = client.rpc(
            "match_memories",
            {
                "query_embedding": embedding,
                "match_threshold": 0.5,
                "match_count": limit,
            }
        ).execute()

        if not response.data:
            return ""

        context_parts = []
        for item in response.data:
            content = item.get("content", "")
            if content:
                context_parts.append(f"- {content}")

        return "\n".join(context_parts)
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        return ""

def add_memory(content: str, metadata: Optional[dict[str, Any]] = None) -> bool:
    """Adds a new text chunk to the memory store.

    Args:
        content: The text content to store.
        metadata: Optional metadata (source_id, etc).

    Returns:
        True if successful, False otherwise.
    """
    try:
        embedding = get_embedding(content)
        if not embedding:
            return False

        client = get_supabase_client()
        payload = {
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {}
        }
        
        client.table("memories").insert(payload).execute()
        return True
    except Exception as e:
        # Check for unique constraint violation (idempotency)
        if "unique_content" in str(e):
            logger.info(f"Memory already exists: {content[:50]}...")
            return True
        logger.error(f"Error adding memory: {e}")
        return False
