"""Pipeline script to fetch and update recent Congress stock transactions.

Pulls latest Senate and House STOCK Act disclosures from FMP and upserts them into Supabase.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import logger
from tools.congress_tools import (
    fetch_congress_trades_from_fmp,
    upsert_congress_trades_to_db,
)


async def run_congress_update(symbol: str | None = None) -> int:
    """Fetch latest Congress trading activity and persist to Supabase."""
    logger.info(f"Starting Congress trading update (symbol={symbol or 'ALL'})...")

    senate_trades = await fetch_congress_trades_from_fmp(chamber="senate", symbol=symbol)
    house_trades = await fetch_congress_trades_from_fmp(chamber="house", symbol=symbol)

    combined = senate_trades + house_trades
    logger.info(f"Fetched {len(senate_trades)} Senate trades and {len(house_trades)} House trades.")

    if not combined:
        logger.warning("No Congress trades retrieved.")
        return 0

    upserted = await upsert_congress_trades_to_db(combined)
    logger.info(f"Successfully upserted {upserted} Congress trades into Supabase.")
    return upserted


def main():
    """CLI entry point for Congress trading update."""
    parser = argparse.ArgumentParser(description="Update Congress stock trading disclosures.")
    parser.add_argument("--symbol", "--ticker", type=str, default=None, help="Optional ticker symbol filter")
    args = parser.parse_args()

    asyncio.run(run_congress_update(symbol=args.symbol))


if __name__ == "__main__":
    main()
