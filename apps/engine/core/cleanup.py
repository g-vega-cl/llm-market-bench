"""Database cleanup logic for CI/CD and maintenance."""

from .config import logger
from .db import get_supabase_client


async def run_cleanup():
    """Perform periodic database cleanup of stale logs and records."""
    sb = get_supabase_client()
    logger.info("Starting database cleanup...")

    try:
        # 1. Cleanup ingestion logs (> 48h)
        # Using Supabase's PostgreSQL date functions via raw strings in filters
        logger.info("Cleaning ingestion_logs older than 48 hours...")
        sb.table("ingestion_logs").delete().lt("created_at", 'now() - interval "48 hours"').execute()

        # 2. Cleanup resolved/ignored audits (> 30 days)
        logger.info("Cleaning resolved/ignored system_audits older than 30 days...")
        sb.table("system_audits").delete().in_("status", ["RESOLVED", "IGNORED"]).lt(
            "created_at", 'now() - interval "30 days"'
        ).execute()

        # 3. Cleanup market feeling records (> 30 days)
        logger.info("Cleaning market_feeling records older than 30 days...")
        sb.table("market_feeling").delete().lt("created_at", 'now() - interval "30 days"').execute()

        # 4. Cleanup superseded memories (> 180 days)
        logger.info("Cleaning SUPERSEDED memories older than 180 days...")
        sb.table("memories").delete().eq("status", "SUPERSEDED").lt(
            "created_at", 'now() - interval "180 days"'
        ).execute()

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
