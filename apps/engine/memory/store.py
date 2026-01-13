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
        error_str = str(e).lower()
        # Check for various unique constraint violation patterns
        is_duplicate = any(pattern in error_str for pattern in [
            "unique_content",           # Named constraint
            "unique constraint",        # Generic PostgreSQL
            "duplicate key",            # PostgreSQL error
            "violates unique",          # PostgreSQL violation message
            "23505",                    # PostgreSQL unique violation code
        ])

        if is_duplicate:
            logger.info(f"Memory already exists (idempotent): {content[:50]}...")
            return True

        logger.error(f"Error adding memory: {e}")
        return False
def check_recent_memories(content: str, threshold: float = 0.85, hours: int = 48) -> bool:
    """Checks if a semantically similar memory exists within the last N hours.

    Args:
        content: The text content to check.
        threshold: Cosine similarity threshold.
        hours: How far back to look.

    Returns:
        True if a similar memory exists, False otherwise.
    """
    try:
        from datetime import datetime, timedelta, timezone
        
        embedding = get_embedding(content)
        if not embedding:
            return False

        client = get_supabase_client()
        
        # We query the table directly with pgvector operators and time filters
        # for maximum precision.
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        # Using Supabase client to perform a vector similarity search with a filter
        # Operator '<=>' is cosine distance (1 - similarity)
        response = client.table("memories").select("id, created_at, content").filter(
            "created_at", "gte", cutoff
        ).order(
            "embedding",  # Note: Sorting by vector in JS/Python client usually requires raw SQL
                          # but we can filter by time first then check similarity in code
                          # or just use the match_memories RPC if we modify it.
                          # For now, let's fetch recent and check cosine similarity in Python 
                          # to avoid needing a migration immediately.
        ).execute()

        if not response.data:
            return False

        # We'll calculate similarity for the recent items
        # In production, this should be done with a modified RPC: 
        # match_memories_with_time(query_embedding, match_threshold, match_count, min_time)
        from consensus import cosine_similarity
        
        recent_embeddings_response = client.table("memories").select("embedding").filter(
            "created_at", "gte", cutoff
        ).execute()
        
        if not recent_embeddings_response.data:
            return False
            
        for row in recent_embeddings_response.data:
            recent_vector = row.get("embedding")
            if recent_vector:
                # Convert string representation to list if necessary
                if isinstance(recent_vector, str):
                    import json
                    recent_vector = json.loads(recent_vector)
                
                sim = cosine_similarity(embedding, recent_vector)
                if sim >= threshold:
                    logger.info(f"Duplicate event found in recent history (Similarity: {sim:.2f})")
                    return True

        return False
    except Exception as e:
        logger.error(f"Error checking recent memories: {e}")
        return False
