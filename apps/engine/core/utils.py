"""General utility functions for the engine."""

import datetime
import logging

from execution.market_data import MarketDataManager

logger = logging.getLogger("engine")


async def is_market_open_with_logging(force: bool = False) -> bool:
    """Checks if the US market is open and logs a warning if closed.

    Args:
        force: If True, always returns True to bypass the check.

    Returns:
        True if the market is open or force is True, False otherwise.
    """
    if force:
        return True

    manager = MarketDataManager()
    if not await manager.is_market_open():
        try:
            from zoneinfo import ZoneInfo

            now = datetime.datetime.now(ZoneInfo("America/New_York"))
        except ImportError:
            now = datetime.datetime.now()

        logger.warning(f"Market is currently closed (Time: {now.strftime('%H:%M')} ET). Use --force to override.")
        return False

    return True
