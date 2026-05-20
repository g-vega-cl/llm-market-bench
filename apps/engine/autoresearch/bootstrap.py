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


async def bootstrap():
    """Insert the initial baseline prompt into the database."""
    logger.info("Checking for active prompt...")
    active = await get_active_prompt()
    if active:
        logger.info("An active prompt already exists. Skipping bootstrap.")
        return

    logger.info("No active prompt found. Bootstrapping with baseline...")

    now = datetime.now(UTC)
    week_start = (now - timedelta(days=7)).date().isoformat()
    week_end = now.date().isoformat()

    tag = await save_variant(
        prompt_content=CORE_ANALYSIS_SYSTEM_PROMPT,
        prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
        week_start=week_start,
        week_end=week_end,
        metrics={"score": 0, "excess_return": 0, "max_drawdown": 0, "note": "Initial baseline"},
        change_description="Initial baseline prompt from source code.",
        experiment_type="baseline",
    )

    logger.info("Successfully bootstrapped with variant: %s", tag)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(bootstrap())
