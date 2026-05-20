import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import asyncio
import logging

from core.db import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clear_db")


async def clear_database():
    """Clear all tables except price_history and market_data_cache."""
    supabase = get_supabase_client()

    # Order matters due to foreign key constraints:
    # 1. decisions depends on trades
    # 2. trades depends on portfolios
    # 3. portfolio_positions and portfolio_performance depend on portfolios

    tables_to_clear = [
        "decisions",
        "trades",
        "portfolio_positions",
        "portfolio_performance",
        "portfolios",
        "newsletter_snapshots",
        "memories",
        "concept_metrics",
    ]

    logger.info("Starting database clear...")

    for table in tables_to_clear:
        try:
            logger.info(f"Clearing table: {table}...")
            # Using a filter that matches everything to bypass "delete without filters" protection
            # if applicable, or using the same pattern as reset_state.py
            supabase.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            logger.info(f"Successfully cleared {table}")
        except Exception as e:
            logger.error(f"Failed to clear table {table}: {e}")
            # We don't raise here to allow other tables to be cleared,
            # but in a script like this, failure usually means constraint issues.

    logger.info("Database clear operation finished.")
    logger.info("Note: price_history and market_data_cache were NOT cleared.")


if __name__ == "__main__":
    asyncio.run(clear_database())
