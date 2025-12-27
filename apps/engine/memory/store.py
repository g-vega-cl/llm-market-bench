"""Supabase pgvector store logic."""

import logging
from typing import Any, Optional
from supabase import Client
from core.db import get_supabase_client
from .embeddings import get_embedding, get_embeddings_batch

logger = logging.getLogger("engine")

def retrieve_context(query_text: str, limit: int = 3) -> str:
    """Retrieves relevant past events/reasoning for a single text snippet."""
    results = retrieve_context_batch([query_text], limit=limit)
    return results[0] if results else ""

def retrieve_context_batch(queries: list[str], limit: int = 3) -> list[str]:
    """Retrieves relevant past events/reasoning for multiple snippets in fewer calls.

    Args:
        queries: List of text snippets to search for.
        limit: Number of relevant snippets to return per query.

    Returns:
        A list of formatted strings, one for each query.
    """
    if not queries:
        return []

    try:
        # 1. Batch generate embeddings (1 API Call)
        embeddings = get_embeddings_batch(queries)
        if not embeddings:
            return ["" for _ in queries]

        client = get_supabase_client()
        results = []

        # 2. Query Supabase for each embedding (DB calls are generally safe/fast,
        # but we could also optimize this with a single custom PG function if needed).
        # For now, consolidating the LLM API call is the primary goal.
        for embedding in embeddings:
            response = client.rpc(
                "match_memories",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.5,
                    "match_count": limit,
                }
            ).execute()

            if not response.data:
                results.append("")
                continue

            context_parts = []
            for item in response.data:
                content = item.get("content", "")
                if content:
                    context_parts.append(f"- {content}")
            
            results.append("\n".join(context_parts))

        return results
    except Exception as e:
        logger.error(f"Error in retrieve_context_batch: {e}")
        return ["" for _ in queries]

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
