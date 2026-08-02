"""Supabase pgvector store logic."""

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from supabase import Client

from core.db import get_supabase_client

from .embeddings import get_embedding, get_embeddings_batch

logger = logging.getLogger("engine")

MAX_RAG_TOKENS = 2000


def strip_html(text: str | None) -> str:
    if not text:
        return text
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def prune_context(items: list[dict], max_tokens: int = MAX_RAG_TOKENS) -> str:
    """Rank items by importance × similarity, cap at token budget, sentence-boundary truncate.

    Args:
        items: List of dicts with 'content', 'importance_score' (optional), 'similarity' (optional).
        max_tokens: Maximum token budget for the formatted output.

    Returns:
        A formatted string with ranked, pruned context.
    """
    if not items:
        return ""

    scored = []
    for item in items:
        importance = item.get("importance_score", 5)
        similarity = item.get("similarity", 0.5)
        content = strip_html(item.get("content", ""))
        signal_type = item.get("label", "")
        ticker = item.get("ticker", "")
        scored.append((importance * similarity, content, signal_type, ticker))

    scored.sort(key=lambda x: x[0], reverse=True)

    lines = []
    tokens_used = 0
    for score, content, signal_type, ticker in scored:
        if not content:
            continue
        if signal_type == "[LESSON_LEARNED]":
            first_sentence = re.split(r"(?<=[.!?])\s+", content)[0]
            content = first_sentence

        if ticker:
            tag = f"[{signal_type}] {ticker}: {content}" if signal_type else f"[PAST REASONING] {ticker}: {content}"
        else:
            imp = int(score) if score > 0 else 5
            tag = f"[{signal_type}] (Importance: {imp}/10) {content}" if signal_type else f"[MEMORY] {content}"

        line_tokens = _estimate_tokens(tag)
        if tokens_used + line_tokens > max_tokens:
            continue
        lines.append(tag)
        tokens_used += line_tokens

    return "\n".join(lines)


def retrieve_top_memories(limit: int = 5, min_importance: int = 7) -> str:
    """Fetches the highest-importance active memories without embedding search.

    Returns a formatted string suitable for injection into analysis prompts.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("memories")
            .select("content, importance_score, memory_type")
            .eq("status", "ACTIVE")
            .gte("importance_score", min_importance)
            .order("importance_score", desc=True)
            .limit(limit)
            .execute()
        )

        if not response.data:
            return ""

        items = []
        for row in response.data:
            mt = row.get("memory_type", "MARKET_EVENT")
            label_map = {
                "MARKET_EVENT": "MARKET EVENT",
                "GOVERNMENT_INCENTIVE": "GOVERNMENT INCENTIVE",
                "LESSON_LEARNED": "LESSON LEARNED",
                "UNCROWDED_TRADE": "UNCROWDED TRADE",
                "POST_MORTEM": "POST MORTEM",
                "ACADEMIC_PAPER": "ACADEMIC PRINCIPLE",
            }
            label = label_map.get(mt, "MARKET EVENT")
            items.append(
                {
                    "content": f"- [{label}] {row['content']}",
                    "importance_score": row.get("importance_score", 5),
                }
            )

        return "\n".join(item["content"] for item in items)
    except Exception as e:
        logger.error(f"Error in retrieve_top_memories: {e}")
        return ""


def retrieve_thematic_flows(limit: int = 5) -> str:
    """Fetches active THEMATIC_FLOW and UNCROWDED_TRADE memories for analysis.

    Returns:
        A formatted string of active thematic flows & macro capital rotations.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("memories")
            .select("content, importance_score, memory_type")
            .eq("status", "ACTIVE")
            .in_("memory_type", ["THEMATIC_FLOW", "UNCROWDED_TRADE"])
            .order("importance_score", desc=True)
            .limit(limit)
            .execute()
        )

        if not response.data:
            return ""

        lines = []
        for row in response.data:
            importance = row.get("importance_score", 5)
            content = strip_html(row.get("content", ""))
            if content:
                lines.append(f"- [THEMATIC FLOW] (Importance: {importance}/10) {content}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error in retrieve_thematic_flows: {e}")
        return ""


def retrieve_uncrowded_trades(limit: int = 5) -> str:
    """Alias for retrieve_thematic_flows for backward compatibility."""
    return retrieve_thematic_flows(limit=limit)


def retrieve_for_decision(
    ticker: str,
    reasoning: str,
    max_tokens: int = MAX_RAG_TOKENS,
    model_name: str | None = None,
) -> str:
    """Targeted semantic search for memories relevant to a specific proposed trade.

    Searches both memories and past decisions tables, ranks by importance × similarity,
    and prunes to the token budget.

    Args:
        ticker: The ticker symbol being traded.
        reasoning: The agent's reasoning for the trade.
        max_tokens: Token budget for the output.
        model_name: If set, filters past decisions to only those from this model.

    Returns:
        A formatted, pruned context string.
    """
    try:
        query = f"{ticker} {reasoning}"
        embedding = get_embedding(query)
        if not embedding:
            return ""

        client = get_supabase_client()

        mem_response = client.rpc(
            "match_memories",
            {
                "query_embedding": embedding,
                "match_threshold": 0.4,
                "match_count": 5,
                "filter_memory_types": None,
            },
        ).execute()

        dec_response = client.rpc(
            "match_decisions",
            {
                "query_embedding": embedding,
                "match_threshold": 0.4,
                "match_count": 3,
                "filter_model_name": model_name,
            },
        ).execute()

        items = []
        if mem_response.data:
            for row in mem_response.data:
                mt = row.get("memory_type", "MARKET_EVENT")
                label_map = {
                    "MARKET_EVENT": "MARKET EVENT",
                    "GOVERNMENT_INCENTIVE": "GOVERNMENT INCENTIVE",
                    "LESSON_LEARNED": "LESSON_LEARNED",
                    "UNCROWDED_TRADE": "UNCROWDED TRADE",
                    "POST_MORTEM": "POST_MORTEM",
                    "ACADEMIC_PAPER": "ACADEMIC PRINCIPLE",
                }
                label = label_map.get(mt, "MARKET EVENT")
                items.append(
                    {
                        "content": row.get("content", ""),
                        "importance_score": row.get("importance_score", 5),
                        "similarity": row.get("similarity", 0.5),
                        "label": label,
                        "ticker": ticker,
                    }
                )

        if dec_response.data:
            for row in dec_response.data:
                items.append(
                    {
                        "content": row.get("reasoning", ""),
                        "importance_score": 5,
                        "similarity": row.get("similarity", 0.5),
                        "label": "PAST REASONING",
                        "ticker": row.get("ticker", ticker),
                    }
                )

        return prune_context(items, max_tokens)
    except Exception as e:
        logger.error(f"Error in retrieve_for_decision: {e}")
        return ""


def retrieve_context(query_text: str, model_name: str, limit: int = 3) -> str:
    """Retrieves relevant past events/reasoning for a single text snippet."""
    results = retrieve_context_batch([query_text], model_name=model_name, limit=limit)
    return results[0] if results else ""


def retrieve_context_batch(
    queries: list[str],
    model_name: str,
    limit: int = 3,
    memory_types: list[str] = None,
    embeddings: list[list[float]] = None,
) -> list[str]:
    """Retrieves relevant past events/reasoning for multiple snippets in fewer calls.

    Args:
        queries: List of text snippets to search for.
        model_name: Scopes trade decision context to this specific agent.
        limit: Number of relevant snippets to return per query.
        memory_types: Optional list of memory types to filter by.
        embeddings: Optional pre-calculated embeddings.

    Returns:
        A list of formatted strings, one for each query.
    """
    if not queries and not embeddings:
        return []

    try:
        # 1. Batch generate embeddings (1 API Call) if not provided
        if embeddings is None:
            embeddings = get_embeddings_batch(queries)
        if not embeddings:
            return ["" for _ in queries]

        client = get_supabase_client()
        results = []

        # 2. Query Supabase for each embedding (DB calls are generally safe/fast,
        # but we could also optimize this with a single custom PG function if needed).
        # For now, consolidating the LLM API call is the primary goal.
        for embedding in embeddings:
            # 2a. Query Memories (Macro Events)
            mem_response = client.rpc(
                "match_memories",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.5,
                    "match_count": limit,
                    "filter_memory_types": memory_types,
                },
            ).execute()

            mem_data = mem_response.data or []

            # 2b. Query Decisions (Trade Reasoning)
            dec_response = client.rpc(
                "match_decisions",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.5,
                    "match_count": limit,
                    "filter_model_name": model_name,
                },
            ).execute()

            context_parts = []

            # Process Memories
            if mem_data:
                for item in mem_data:
                    content = item.get("content", "")
                    importance = item.get("importance_score", 5)
                    if content:
                        context_parts.append(f"- [MARKET EVENT] (Importance: {importance}/10) {content}")

            # Process Decisions
            if dec_response.data:
                for item in dec_response.data:
                    ticker = item.get("ticker", "UNKNOWN")
                    signal = item.get("signal", "UNKNOWN")
                    reasoning = item.get("reasoning", "")
                    if reasoning:
                        context_parts.append(f"- [PAST REASONING (HISTORICAL)] {ticker} {signal}: {reasoning}")

            if not context_parts:
                results.append("")
            else:
                # Limit to total limit per query (e.g. top 3 combined)
                # For now, let's keep all from both but maybe truncate if too long
                results.append("\n".join(context_parts[: limit * 2]))

        return results
    except Exception as e:
        logger.error(f"Error in retrieve_context_batch: {e}")
        return ["" for _ in queries]


def find_potential_ancestors(query_text: str, limit: int = 5, threshold: float = 0.5) -> list[dict]:
    """Finds candidate memories that could be ancestors of a new event.

    Args:
        query_text: The text to search for.
        limit: Max number of candidates.
        threshold: Similarity threshold.

    Returns:
        List of memory records (id, content, status).
    """
    try:
        embedding = get_embedding(query_text)
        if not embedding:
            return []

        client = get_supabase_client()
        response = client.rpc(
            "match_memories",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": limit,
                "filter_memory_types": None,
            },
        ).execute()

        return response.data or []
    except Exception as e:
        logger.error(f"Error finding potential ancestors: {e}")
        return []


def find_similar_memory(
    content: str,
    threshold: float = 0.90,
    hours: int = 24,
    embedding: list[float] = None,
) -> str | None:
    """Checks if a semantically similar memory exists within the last N hours.

    Returns:
        The ID of the similar memory if found, None otherwise.
    """
    row = find_similar_vector(
        table_name="memories",
        content=content,
        threshold=threshold,
        hours=hours,
        embedding=embedding,
        status_filter="ACTIVE",
    )
    return row.get("id") if row else None


def find_similar_decision(
    ticker: str,
    content: str,
    threshold: float = 0.90,
    hours: int = 24,
    embedding: list[float] = None,
    model_name: str | None = None,
) -> dict | None:
    """Checks if a semantically similar trade decision exists for this ticker within the last N hours.

    Args:
        ticker: The ticker symbol to check.
        content: The reasoning text to compare.
        threshold: Similarity threshold (0.0-1.0).
        hours: Lookback window in hours.
        embedding: Pre-computed embedding (optional).
        model_name: Filter by agent/model name to ensure semantic overlap only applies within the same agent.

    Returns:
        The similar decision record if found, None otherwise.
    """
    return find_similar_vector(
        table_name="decisions",
        content=content,
        threshold=threshold,
        hours=hours,
        embedding=embedding,
        ticker_filter=ticker,
        model_name_filter=model_name,
    )


def find_similar_vector(
    table_name: str,
    content: str,
    threshold: float = 0.90,
    hours: int = 24,
    embedding: list[float] = None,
    status_filter: str | None = None,
    ticker_filter: str | None = None,
    model_name_filter: str | None = None,
) -> Any | None:
    """Generic semantic similarity check across tables with embeddings."""
    try:
        if embedding is None:
            embedding = get_embedding(content)

        if not embedding:
            return None

        client = get_supabase_client()
        cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()

        query = client.table(table_name).select("*").filter("created_at", "gte", cutoff)

        if status_filter:
            query = query.filter("status", "eq", status_filter)
        if ticker_filter:
            query = query.filter("ticker", "eq", ticker_filter)
        if model_name_filter:
            query = query.filter("model_name", "eq", model_name_filter)

        recent_res = query.execute()

        if not recent_res.data:
            return None

        from analysis.consensus import cosine_similarity

        for row in recent_res.data:
            recent_vector = row.get("embedding")
            if recent_vector:
                if isinstance(recent_vector, str):
                    import json

                    recent_vector = json.loads(recent_vector)

                sim = cosine_similarity(embedding, recent_vector)

                if sim >= threshold:
                    logger.info(f"Similar {table_name} found (ID: {row['id']}, Sim: {sim:.2f})")
                    return row

        return None
    except Exception as e:
        logger.error(f"Error checking similar vectors in {table_name}: {e}")
        return None


def update_memory_status(memory_id: str, status: str) -> bool:
    """Updates the status of an existing memory.

    Args:
        memory_id: The UUID of the memory to update.
        status: The new status (ACTIVE, RESOLVED, SUPERSEDED).

    Returns:
        True if successful, False otherwise.
    """
    try:
        client = get_supabase_client()
        client.table("memories").update({"status": status}).eq("id", memory_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating memory status: {e}")
        return False


def add_memory(
    content: str,
    metadata: dict[str, Any] | None = None,
    parent_id: str | None = None,
    status: str = "ACTIVE",
    relationship_type: str | None = None,
    target_date: str | None = None,
    memory_type: str = "MARKET_EVENT",
    check_similarity: bool = False,
    similarity_threshold: float = 0.90,
    lookback_hours: int = 168,
    importance_score: int = 5,
) -> str | None:
    """Adds a new text chunk to the memory store.

    Args:
        content: The text content to store.
        metadata: Optional metadata (source_id, etc).
        parent_id: Optional reference to a previous memory ID.
        status: The initial status of the memory (ACTIVE, RESOLVED, SUPERSEDED).
        relationship_type: Type of relationship to parent (REVERSAL, UPDATE, RESOLUTION, GENERAL).
        memory_type: Categorization (MARKET_EVENT, GOVERNMENT_INCENTIVE, LESSON_LEARNED).
        check_similarity: Whether to perform semantic deduplication before insertion.
        similarity_threshold: Threshold for duplicate detection (0.0 to 1.0).
        lookback_hours: How many hours to look back for duplicates.

    Returns:
        The ID of the new memory if successful, None otherwise.
    """
    try:
        embedding = get_embedding(content)
        if not embedding:
            return None

        if check_similarity:
            similar_id = find_similar_memory(content, similarity_threshold, lookback_hours, embedding=embedding)
            if similar_id:
                logger.info(
                    f"Reinforcing memory: Semantic duplicate of {similar_id}. Boosting relevance and bumping timestamp."
                )
                client = get_supabase_client()
                client.table("memories").update(
                    {"relevance_score": 1.0, "created_at": datetime.now(UTC).isoformat()}
                ).eq("id", similar_id).execute()
                return similar_id

        client = get_supabase_client()
        payload = {
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "status": status,
            "parent_id": parent_id,
            "relationship_type": relationship_type,
            "target_date": target_date,
            "memory_type": memory_type,
            "importance_score": importance_score,
        }

        response = client.table("memories").insert(payload).execute()
        if response.data:
            return response.data[0]["id"]
        return None
    except Exception as e:
        error_str = str(e).lower()
        # Check for various unique constraint violation patterns
        is_duplicate = any(
            pattern in error_str
            for pattern in [
                "unique_content",  # Named constraint
                "unique constraint",  # Generic PostgreSQL
                "duplicate key",  # PostgreSQL error
                "violates unique",  # PostgreSQL violation message
                "23505",  # PostgreSQL unique violation code
            ]
        )

        if is_duplicate:
            logger.info(f"Memory already exists (idempotent): {content[:50]}...")
            # If duplicate, we might want to return the existing ID
            # For now, let's just return None or fetch it if needed.
            # Simple approach: return None as it's not "newly added"
            return None

        logger.error(f"Error adding memory: {e}")
        return None


def decay_memories(sb_client: Client, decay_days: int = None):
    """Apply time-based decay to relevance scores of memories not updated recently.

    Memories that haven't been mentioned in `decay_days` have their relevance
    reduced by 50% (half-life decay model).

    Args:
        sb_client: Supabase client instance.
        decay_days: Number of days of inactivity before decay applies.
            Defaults to MEMORIES_RELEVANCE_DECAY_HALF_LIFE_DAYS from config.
    """
    from core import config

    decay_days = decay_days or config.MEMORIES_RELEVANCE_DECAY_HALF_LIFE_DAYS
    cutoff = (datetime.now(UTC) - timedelta(days=decay_days)).isoformat()

    try:
        # Fetch active memories with relevance > threshold
        response = (
            sb_client.table("memories")
            .select("id", "relevance_score", "created_at", "memory_type")
            .eq("status", "ACTIVE")
            .lt("created_at", cutoff)
            .gt("relevance_score", config.MEMORIES_DECAY_THRESHOLD)
            .execute()
        )

        if not response.data:
            logger.info("No stale memories to decay.")
            return

        decay_count = 0
        for memory in response.data:
            mt = memory.get("memory_type", "MARKET_EVENT")
            if mt in ("LESSON_LEARNED", "POST_MORTEM", "ACADEMIC_PAPER"):
                continue  # Never decay: behavioral patterns and immutable trade outcomes

            # THEMATIC_FLOW / UNCROWDED_TRADE: cycle-specific theses decay slowly.
            # 0.72/month → relevant for ~2 months, below 0.05 threshold by month 12.
            # This lets AI-rotation style theses fade naturally as the cycle turns.
            if mt in ("THEMATIC_FLOW", "UNCROWDED_TRADE"):
                decay_factor = 0.72
            elif mt == "MARKET_EVENT":
                decay_factor = 0.5   # 50% per 30 days
            else:
                decay_factor = 0.75  # 25% decay for GOVERNMENT_INCENTIVE and others
            new_relevance = memory["relevance_score"] * decay_factor
            sb_client.table("memories").update({"relevance_score": new_relevance}).eq("id", memory["id"]).execute()
            decay_count += 1

        logger.info(f"Decayed relevance for {decay_count} stale memories.")
    except Exception as e:
        logger.error(f"Error decaying stale memories: {e}")


def get_top_trending_concepts(limit: int = 5) -> str:
    """Fetches the highest velocity concepts from the concept map.

    Args:
        limit: Number of concepts to return.

    Returns:
        A formatted string of trending concepts for LLM context.
    """
    try:
        client = get_supabase_client()
        # Fetch concepts ordered by velocity_score descending
        response = (
            client.table("concept_metrics")
            .select("concept_name, velocity_score, mention_count")
            .order("velocity_score", desc=True)
            .limit(limit)
            .execute()
        )

        if not response.data:
            return ""

        lines = ["### Top Trending Market Concepts (from Concept Map):"]
        for row in response.data:
            name = row.get("concept_name", "Unknown")
            vel = row.get("velocity_score", 0.0)
            count = row.get("mention_count", 0)
            lines.append(f"- {name} (Velocity: {vel:.2f}, Mentions: {count})")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error fetching trending concepts: {e}")
        return ""


async def consolidate_overlapping_memories(similarity_threshold: float = 0.85):
    """Weekly offline consolidation of active memories into synthesized canonical entries.

    Identifies clusters of active memories with cosine similarity > threshold,
    synthesizes them using DeepSeek, inserts the consolidated memory, and marks the
    original pieces as SUPERSEDED.
    """
    try:
        import asyncio
        import json
        from typing import Literal

        from pydantic import BaseModel, Field

        from analysis.consensus import cosine_similarity
        from core.config import DEEPSEEK_MODEL
        from core.llm import get_deepseek_client
        from core.llm.prompt_factory import PromptFactory

        class ConsolidationResponse(BaseModel):
            headline: str = Field(..., description="Concise headline for the consolidated memory")
            summary: str = Field(..., description="Comprehensive summary of the consolidated events")
            importance_score: int = Field(..., ge=1, le=10, description="Synthesized importance score (1-10)")
            memory_type: Literal["MARKET_EVENT", "GOVERNMENT_INCENTIVE"] = Field(
                ..., description="Consolidated memory type"
            )

        client = get_supabase_client()
        # 1. Fetch all ACTIVE memories (capped at 500 most recent for scaling scale safety)
        response = (
            client.table("memories")
            .select("id", "content", "embedding", "importance_score", "memory_type")
            .eq("status", "ACTIVE")
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )

        if not response.data or len(response.data) < 2:
            logger.info("Not enough active memories for consolidation.")
            return

        memories = response.data
        # Ensure we parse string embeddings if they are returned as string JSON
        for m in memories:
            emb = m.get("embedding")
            if isinstance(emb, str):
                m["embedding"] = json.loads(emb)

        # Filter out memories without embeddings
        memories = [m for m in memories if m.get("embedding") is not None]

        # 2. Find connected components of similar memories (adjacency list)
        adj = {m["id"]: [] for m in memories}
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                m1 = memories[i]
                m2 = memories[j]
                if cosine_similarity(m1["embedding"], m2["embedding"]) >= similarity_threshold:
                    adj[m1["id"]].append(m2["id"])
                    adj[m2["id"]].append(m1["id"])

        # Find connected components (DFS)
        visited = set()
        components = []
        for m in memories:
            m_id = m["id"]
            if m_id not in visited:
                comp = []
                queue = [m_id]
                visited.add(m_id)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                if len(comp) >= 2:
                    components.append(comp)

        if not components:
            logger.info("No overlapping memory clusters found for consolidation.")
            return

        # Map ID to memory dictionary
        memory_map = {m["id"]: m for m in memories}
        deepseek = get_deepseek_client()

        for comp in components:
            logger.info(f"Consolidating overlapping cluster of {len(comp)} memories: {comp}")

            # Format cluster content for LLM synthesis prompt
            cluster_memories = [memory_map[m_id] for m_id in comp]
            formatted_memories = []
            for idx, m in enumerate(cluster_memories):
                formatted_memories.append(
                    f"Memory {idx + 1} [ID: {m['id']}, Type: {m['memory_type']}, Importance: {m['importance_score']}]: {m['content']}"
                )

            overlapping_text = "\n".join(formatted_memories)

            # Build prompts
            messages = PromptFactory.build_memory_consolidation_messages(
                provider="deepseek", overlapping_memories=overlapping_text
            )

            # Call DeepSeek (via config.DEEPSEEK_MODEL) via instructor
            resp_awaitable = deepseek.chat.completions.create(
                model=DEEPSEEK_MODEL, response_model=ConsolidationResponse, messages=messages
            )

            if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
                resp = await resp_awaitable
            else:
                resp = resp_awaitable

            # 3. Create the consolidated memory content
            consolidated_content = f"[CONSOLIDATED] {resp.headline} | {resp.summary}"

            # Use the first memory in the cluster as the primary parent_id
            primary_parent = cluster_memories[0]["id"]

            # Metadata holds all original consolidated memory IDs
            metadata = {
                "consolidated_ids": comp,
                "consolidation_headline": resp.headline,
            }

            # Add the new synthesized consolidated memory
            new_id = add_memory(
                content=consolidated_content,
                metadata=metadata,
                parent_id=primary_parent,
                status="ACTIVE",
                relationship_type="UPDATE",
                memory_type=resp.memory_type,
                importance_score=resp.importance_score,
                check_similarity=False,  # Skip check since this is a new consolidated memory
            )

            if new_id:
                logger.info(f"Created new consolidated memory {new_id} for cluster.")
                # Mark older memories in the cluster as SUPERSEDED
                for m_id in comp:
                    update_memory_status(m_id, "SUPERSEDED")
            else:
                logger.error(f"Failed to create consolidated memory for cluster {comp}")

    except Exception as e:
        logger.error(f"Error in consolidate_overlapping_memories: {e}")
