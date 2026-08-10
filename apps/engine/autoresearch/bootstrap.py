"""Bootstrap utility for auto-research.

Initializes the prompt_experiments table with a baseline variant.
Run via: python -m autoresearch.bootstrap  (from apps/engine/ with venv active)
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from autoresearch.prompt_store import get_active_prompt, save_variant
from core.config import logger
from core.llm.prompts import CORE_ANALYSIS_SYSTEM_PROMPT


async def bootstrap(track_id: str = "track_default") -> str | None:
    """Insert the initial baseline prompt into the database."""
    logger.info("Checking for active prompt for track_id=%s...", track_id)
    try:
        active = await get_active_prompt(track_id=track_id)
    except TypeError:
        active = await get_active_prompt()

    if active:
        logger.info("An active prompt already exists for track_id=%s. Skipping bootstrap.", track_id)
        return None

    logger.info("No active prompt found for track_id=%s. Bootstrapping with baseline...", track_id)

    now = datetime.now(UTC)
    week_start = (now - timedelta(days=7)).date().isoformat()
    week_end = now.date().isoformat()

    try:
        tag = await save_variant(
            prompt_content=CORE_ANALYSIS_SYSTEM_PROMPT,
            prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
            week_start=week_start,
            week_end=week_end,
            metrics={"score": 0, "excess_return": 0, "max_drawdown": 0, "note": "Initial baseline"},
            change_description="Initial baseline prompt from source code.",
            experiment_type="baseline",
            research_output={"selected_tools": ["get_portfolio_ledger", "get_todays_news_menu", "web_search"]},
            track_id=track_id,
        )
    except TypeError:
        tag = await save_variant(
            prompt_content=CORE_ANALYSIS_SYSTEM_PROMPT,
            prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
            week_start=week_start,
            week_end=week_end,
            metrics={"score": 0, "excess_return": 0, "max_drawdown": 0, "note": "Initial baseline"},
            change_description="Initial baseline prompt from source code.",
            experiment_type="baseline",
            research_output={"selected_tools": ["get_portfolio_ledger", "get_todays_news_menu", "web_search"]},
        )

    logger.info("Successfully bootstrapped track_id=%s with variant: %s", track_id, tag)
    return tag


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(bootstrap())
