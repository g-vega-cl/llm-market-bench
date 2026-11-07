"""Government budget, macro liquidity, and procurement ingestion pipeline.

Performs scheduled ingestion for:
- US Treasury General Account (TGA) cash, National Debt, and Deficits
- USAspending federal contract awards
- CanadaBuys procurement & Canadian infrastructure contracts
- High-impact government policy catalysts for Catalyst Radar
"""

import asyncio
from typing import Any

from core.config import GEMINI_MODEL, logger
from core.db import get_supabase_client
from core.llm import get_gemini_client
from core.models import DecisionsResponse
from ingest.government_fetchers import (
    fetch_canadabuys_contracts,
    fetch_us_treasury_liquidity,
    fetch_usaspending_contracts,
    upsert_gov_contracts,
    upsert_gov_macro_liquidity,
)
from ingest.whale_fetchers import ingest_institutional_whales
from memory.store import add_memory


class GovernmentPipeline:
    """Ingestion pipeline for tracking government debt, liquidity, and contracts."""

    def __init__(self):
        try:
            self.client = get_gemini_client()
        except Exception:
            self.client = None
        try:
            self.sb_client = get_supabase_client()
        except Exception:
            self.sb_client = None

    async def ingest_liquidity(self, days: int = 14) -> int:
        """Fetch and persist US Treasury liquidity and national debt."""
        records = await fetch_us_treasury_liquidity(days=days)
        if records:
            upserted = await upsert_gov_macro_liquidity(records)
            logger.info("Upserted %d gov macro liquidity records.", upserted)
            return upserted
        return 0

    async def ingest_contracts(self, limit: int = 50) -> dict[str, int]:
        """Fetch and persist US and Canadian government contracts."""
        us_contracts = await fetch_usaspending_contracts(days=14, limit=limit)
        ca_contracts = await fetch_canadabuys_contracts(limit=limit)

        us_count = await upsert_gov_contracts(us_contracts) if us_contracts else 0
        ca_count = await upsert_gov_contracts(ca_contracts) if ca_contracts else 0

        logger.info("Upserted %d US contracts and %d Canada contracts.", us_count, ca_count)
        return {"us_contracts": us_count, "ca_contracts": ca_count}

    async def ingest_whales(self, symbols: list[str] | None = None) -> dict[str, int]:
        """Fetch and persist institutional whale & activist blockholder stakes."""
        res = await ingest_institutional_whales(symbols=symbols)
        logger.info(
            "Upserted %d whale stakes across %d symbols.",
            res["stakes_upserted"],
            res["symbols_processed"],
        )
        return res

    async def extract_policy_memories(self) -> int:
        """Analyze upcoming federal policies and incentives for the Catalyst Radar."""
        if not self.client:
            return 0

        prompt = """Identify current and upcoming US & Canadian government budgets, objectives, and incentives
        that could impact the financial markets. Focus on:
        1. Renewable energy incentives (Inflation Reduction Act, etc.)
        2. Infrastructure and pipeline spending.
        3. Tech and AI-related subsidies or regulations.
        4. Critical minerals initiatives.
        5. Major budget expiration dates.

        Provide a list of major events/incentives.
        """
        try:
            create_call = self.client.chat.completions.create(
                model=GEMINI_MODEL,
                response_model=DecisionsResponse,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a government policy analyst for a hedge fund. Return structured JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            if asyncio.iscoroutine(create_call) or hasattr(create_call, "__await__"):
                res = await create_call
            else:
                res = create_call

            count = 0
            for event in getattr(res, "macro_events", []):
                memory_content = (
                    f"[GOVERNMENT INCENTIVE] {event.event_name}: {event.reasoning} | "
                    f"Impact: {event.impact} | Expiry: {event.expiry_date or 'N/A'}"
                )
                success = add_memory(
                    content=memory_content,
                    memory_type="GOVERNMENT_INCENTIVE",
                    target_date=event.expiry_date,
                    metadata={"expiry_date": event.expiry_date, "impact": event.impact},
                    check_similarity=True,
                )
                if success:
                    count += 1

            logger.info("Added %d government incentive memories.", count)
            return count
        except Exception as e:
            logger.warning("Government policy memory extraction skipped or failed: %s", e)
            return 0

    async def run(self) -> int:
        """Executes the full government ingestion pipeline."""
        logger.info("Starting Government Pipeline run...")

        # 1. Ingest real macro liquidity (TGA cash balance + national debt)
        try:
            await self.ingest_liquidity()
        except Exception as e:
            logger.warning("Liquidity ingestion error: %s", e)

        # 2. Ingest real procurement & contract awards (USAspending + CanadaBuys)
        try:
            await self.ingest_contracts()
        except Exception as e:
            logger.warning("Contracts ingestion error: %s", e)

        # 3. Ingest institutional whale stakes (Schedule 13D/13G)
        try:
            await self.ingest_whales()
        except Exception as e:
            logger.warning("Whale ingestion error: %s", e)

        # 4. Extract policy & incentive memories for catalyst radar
        memories_count = await self.extract_policy_memories()

        logger.info("Government pipeline completed.")
        return memories_count


async def run_government_pipeline() -> dict[str, Any]:
    """Entry point for CLI and scheduled pipeline runs."""
    pipeline = GovernmentPipeline()
    memories_count = await pipeline.run()
    return {"status": "success", "memories_created": memories_count}
