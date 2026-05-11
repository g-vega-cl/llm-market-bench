"""Bootstrap utility for auto-research.

Initializes the prompt_experiments table with a baseline variant.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta

# Add apps/engine to path
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from autoresearch.prompt_store import save_variant, get_active_prompt
from core.llm.prompts import CORE_ANALYSIS_SYSTEM_PROMPT
from core.config import logger

async def bootstrap():
    """Insert the initial baseline prompt into the database."""
    logger.info("Checking for active prompt...")
    active = await get_active_prompt()
    if active:
        logger.info("An active prompt already exists. Skipping bootstrap.")
        return

    logger.info("No active prompt found. Bootstrapping with baseline...")

    # We use a dummy week window for the baseline
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=7)).date().isoformat()
    week_end = now.date().isoformat()

    tag = await save_variant(
        prompt_content=CORE_ANALYSIS_SYSTEM_PROMPT,
        prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
        week_start=week_start,
        week_end=week_end,
        metrics={"composite": 0.5, "note": "Initial baseline"},
        change_description="Initial baseline prompt from source code.",
        experiment_type="baseline"
    )

    logger.info("Successfully bootstrapped with variant: %s", tag)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(bootstrap())
