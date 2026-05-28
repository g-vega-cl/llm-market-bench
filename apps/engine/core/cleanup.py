"""Database cleanup logic for CI/CD and maintenance.

This module provides a unified, secure database maintenance interface called during
the weekly system audit pipeline. It implements robust retention policies for logs,
audits, market feelings, and superseded vector memories.

Security & Parameterization Design:
  Rather than executing raw PostgreSQL date functions (e.g., 'now() - interval "48 hours"')
  which are subject to implicit database coercion and bypass safe query parameterization,
  this module calculates timezone-aware UTC datetime cutoffs in Python. These cutoffs
  are formatted as ISO 8601 strings and passed as safe literals to the PostgREST / Supabase
  client. This eliminates timezone discrepancies between runner/server environments and
  guarantees that all filter values are parsed as safe parameters.
"""

from datetime import UTC, datetime, timedelta

from .config import logger
from .db import get_supabase_client


async def run_cleanup():
    """Perform periodic database cleanup of stale logs and records.

    This function coordinates the following 6 database maintenance stages:
      1. Ingestion Logs: Prunes metadata log records older than 48 hours.
      2. System Audits: Deletes closed/resolved/ignored logs older than 30 days.
      3. Market Feelings: Discards outdated classification metrics older than 30 days.
      4. Superseded Memories: Purges older iterations of consolidated vector memories (> 180 days).
      5. Memory Decay: Triggers the tiered decay protocol for non-strategic memory elements.
      6. Memory Consolidation: Performs the DeepSeek-powered dfs consolidation ("sleep" cycle).

    Raises:
        Exception: Propagates any database/connection exceptions after logging a
                   traceback via logger.exception for full observability.
    """
    sb = get_supabase_client()
    logger.info("Starting database cleanup...")
    now = datetime.now(UTC)

    try:
        # 1. Cleanup ingestion logs (> 48h)
        logger.info("Cleaning ingestion_logs older than 48 hours...")
        threshold_48h = (now - timedelta(hours=48)).isoformat()
        sb.table("ingestion_logs").delete().lt("created_at", threshold_48h).execute()

        # 2. Cleanup resolved/ignored audits (> 30 days)
        logger.info("Cleaning resolved/ignored system_audits older than 30 days...")
        threshold_30d = (now - timedelta(days=30)).isoformat()
        sb.table("system_audits").delete().in_("status", ["RESOLVED", "IGNORED"]).lt(
            "created_at", threshold_30d
        ).execute()

        # 3. Cleanup market feeling records (> 30 days)
        logger.info("Cleaning market_feeling records older than 30 days...")
        sb.table("market_feeling").delete().lt("created_at", threshold_30d).execute()

        # 4. Cleanup superseded memories (> 180 days)
        logger.info("Cleaning SUPERSEDED memories older than 180 days...")
        threshold_180d = (now - timedelta(days=180)).isoformat()
        sb.table("memories").delete().eq("status", "SUPERSEDED").lt("created_at", threshold_180d).execute()

        # 5. Decay stale memories
        logger.info("Decaying stale memories...")
        from memory.store import decay_memories

        decay_memories(sb)

        # 6. Consolidate overlapping memories ("Sleep" cycle)
        logger.info("Consolidating overlapping memories...")
        from memory.store import consolidate_overlapping_memories

        await consolidate_overlapping_memories()

        logger.info("Database cleanup complete.")

    except Exception:
        logger.exception("Database cleanup failed")
        raise
