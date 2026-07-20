"""Bootstrap utility for System-Heavy Auto-Research.

Injects the new logic-dense System Prompt into the database as the active baseline.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from autoresearch.prompt_store import save_variant
from core.config import logger
from core.llm.prompts import CORE_ANALYSIS_SYSTEM_PROMPT


async def bootstrap():
    """Insert the new System-Heavy baseline prompt into the database."""
    logger.info("Bootstrapping System-Heavy Baseline...")

    now = datetime.now(UTC)
    # Set week range to cover the current period
    week_start = (now - timedelta(days=7)).date().isoformat()
    week_end = now.date().isoformat()

    tag = await save_variant(
        prompt_content=CORE_ANALYSIS_SYSTEM_PROMPT,
        prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
        week_start=week_start,
        week_end=week_end,
        metrics={"score": 0, "excess_return": 0, "max_drawdown": 0, "note": "System-Heavy Baseline"},
        change_description="Refactored System-Heavy architecture: moved trading logic from User to System message.",
        experiment_type="baseline",
        research_output={"selected_tools": ["get_portfolio_ledger", "get_todays_news_menu", "web_search"]},
    )

    logger.info("Successfully bootstrapped with variant: %s", tag)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(bootstrap())
