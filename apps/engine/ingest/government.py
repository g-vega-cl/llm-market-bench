"""Government budget and policy ingestion pipeline.

This module performs monthly checks for government budgets, objectives,
and incentives to inform the trading agents.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from core.db import get_supabase_client
from core.llm import get_gemini_client, prompts
from core.config import GEMINI_MODEL, logger
from core.models import MacroEvent, DecisionsResponse
from memory.store import add_memory

class GovernmentPipeline:
    """Monthly pipeline for tracking government budgets and incentives."""

    def __init__(self):
        self.client = get_gemini_client()
        self.sb_client = get_supabase_client()

    async def run(self):
        """Executes the monthly government check."""
        logger.info("Starting Monthly Government Budget & Policy check...")

        # In a real scenario, we'd use a search tool here.
        # For now, we'll ask Gemini to use its internal knowledge or search if tools are enabled.
        # Note: We can add 'google_search_retrieval' tool to Gemini in handlers if supported.

        prompt = """Identify current and upcoming US government budgets, objectives, and incentives
        that could impact the financial markets. Focus on:
        1. Renewable energy incentives (Inflation Reduction Act, etc.)
        2. Infrastructure spending.
        3. Tech and AI-related subsidies or regulations.
        4. Major budget expiration dates (e.g., when the 2026 budget expires).

        Provide a list of major events/incentives.
        """

        try:
            # We use DecisionsResponse but primarily interested in macro_events
            # We'll use a specialized prompt if needed, but the MacroEvent model has what we need
            res = await self.client.chat.completions.create(
                model=GEMINI_MODEL,
                response_model=DecisionsResponse,
                messages=[
                    {"role": "system", "content": "You are a government policy analyst for a hedge fund. Return structured JSON."},
                    {"role": "user", "content": prompt}
                ]
            )

            count = 0
            for event in res.macro_events:
                # Save to memories as GOVERNMENT_INCENTIVE
                memory_content = (
                    f"[GOVERNMENT INCENTIVE] {event.event_name}: {event.reasoning} | "
                    f"Impact: {event.impact} | Expiry: {event.expiry_date or 'N/A'}"
                )

                success = add_memory(
                    content=memory_content,
                    memory_type="GOVERNMENT_INCENTIVE",
                    target_date=event.expiry_date,
                    metadata={
                        "is_government_incentive": True,
                        "expiry_date": event.expiry_date,
                        "impact": event.impact
                    }
                )
                if success:
                    count += 1

            logger.info(f"Government pipeline complete. Added {count} new memories.")
            return count

        except Exception as e:
            logger.error(f"Government pipeline failed: {e}")
            return 0

async def run_government_pipeline():
    """Entry point for the government pipeline."""
    pipeline = GovernmentPipeline()
    await pipeline.run()
