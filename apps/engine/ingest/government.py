"""Government budget, macro liquidity, and procurement ingestion pipeline.

Performs scheduled ingestion for:
- US Treasury General Account (TGA) cash, National Debt, and Deficits
- USAspending federal contract awards
- CanadaBuys procurement & Canadian infrastructure contracts
- High-impact government policy catalysts for Catalyst Radar
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from core.config import GEMINI_MODEL, logger
from core.db import get_supabase_client
from core.llm import get_gemini_client
from core.models import DecisionsResponse
from ingest.congress_fetchers import (
    fetch_latest_congress_trades,
    upsert_congress_trades,
)
from ingest.federal_register import fetch_federal_register_documents
from ingest.government_fetchers import (
    fetch_canadabuys_contracts,
    fetch_us_treasury_liquidity,
    fetch_usaspending_contracts,
    upsert_gov_contracts,
    upsert_gov_macro_liquidity,
)
from ingest.insider_fetchers import (
    fetch_latest_insider_trades,
    fetch_universe_insider_trades,
    upsert_insider_trades,
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

    async def ingest_congress(self, limit: int = 50) -> int:
        """Fetch and persist recent Congress STOCK Act disclosures."""
        trades = await fetch_latest_congress_trades(limit=limit)
        upserted = await upsert_congress_trades(trades) if trades else 0
        logger.info("Upserted %d congress trades.", upserted)
        return upserted

    async def ingest_insiders(self, limit: int = 50) -> int:
        """Fetch and persist latest Form 4 and active universe corporate/Canadian insider trades."""
        latest_trades = await fetch_latest_insider_trades(limit=limit)
        universe_trades = await fetch_universe_insider_trades(limit_per_symbol=10)

        all_trades = latest_trades + universe_trades
        upserted = await upsert_insider_trades(all_trades) if all_trades else 0
        logger.info("Upserted %d insider trades.", upserted)
        return upserted

    def _load_policy_db_grounding(self) -> list[str]:
        """Load balanced US/CA contracts, Treasury liquidity, and recent newsletter sections synchronously."""
        if not self.sb_client:
            return []

        db_sections: list[str] = []
        date_cutoff = (datetime.now(UTC) - timedelta(days=30)).date().isoformat()
        ts_cutoff = (datetime.now(UTC) - timedelta(days=14)).isoformat()

        try:
            contracts: list[dict[str, Any]] = []
            for country in ("US", "CA"):
                c_res = (
                    self.sb_client.table("gov_contracts")
                    .select("country, recipient_name, award_amount, agency_name, award_date, description")
                    .eq("country", country)
                    .gte("award_date", date_cutoff)
                    .order("award_date", desc=True)
                    .limit(4)
                    .execute()
                )
                contracts.extend(getattr(c_res, "data", None) or [])
            if contracts:
                contract_lines = ["## Recent Sovereign Procurement Awards"]
                for c in contracts:
                    amt = float(c.get("award_amount") or 0.0)
                    contract_lines.append(
                        f"- [{c.get('award_date')}] {c.get('country')} | {c.get('agency_name') or 'Agency'} "
                        f"-> {c.get('recipient_name')}: ${amt:,.0f} ({(c.get('description') or '')[:160]})"
                    )
                db_sections.append("\n".join(contract_lines))
        except Exception:
            logger.exception("Failed loading gov_contracts for policy grounding")

        try:
            liq_res = (
                self.sb_client.table("gov_macro_liquidity")
                .select("record_date, tga_balance, tot_pub_debt, monthly_deficit_surplus")
                .gte("record_date", date_cutoff)
                .order("record_date", desc=True)
                .limit(2)
                .execute()
            )
            liq_rows = getattr(liq_res, "data", None) or []
            if liq_rows:
                latest = liq_rows[0]
                tga = float(latest.get("tga_balance") or 0.0)
                deficit = float(latest.get("monthly_deficit_surplus") or 0.0)
                db_sections.append(
                    "## Latest US Treasury Liquidity Snapshot\n"
                    f"- Date: {latest.get('record_date')} | TGA Balance: ${tga:,.0f} | "
                    f"Monthly Surplus/Deficit: ${deficit:,.0f}"
                )
        except Exception:
            logger.exception("Failed loading gov_macro_liquidity for policy grounding")

        try:
            news_res = (
                self.sb_client.table("generated_newsletters")
                .select("title, summary, created_at")
                .gte("created_at", ts_cutoff)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            news_rows = getattr(news_res, "data", None) or []
            if news_rows:
                summary = (news_rows[0].get("summary") or "")[:1200]
                if summary:
                    db_sections.append(f"## Latest Market Newsletter Summary\n{summary}")
        except Exception:
            logger.exception("Failed loading generated_newsletters for policy grounding")

        return db_sections

    async def fetch_policy_grounding_context(self) -> str:
        """Assemble grounded federal policy documents, sovereign contracts, and macro liquidity context."""
        sections: list[str] = []

        fr_docs, db_sections = await asyncio.gather(
            fetch_federal_register_documents(limit=8),
            asyncio.to_thread(self._load_policy_db_grounding),
        )
        if fr_docs:
            fr_lines = ["## Recent Significant Federal Register Rules & Notices"]
            for doc in fr_docs:
                agencies = ", ".join(doc.get("agency_names") or []) or "Federal Agency"
                pub_date = doc.get("publication_date") or "Unknown"
                abstract = doc.get("abstract") or ""
                fr_lines.append(
                    f"- [{pub_date}] ({agencies}) {doc.get('title')} "
                    f"[Doc #{doc.get('document_number', 'N/A')}]: {abstract}"
                )
            sections.append("\n".join(fr_lines))

        sections.extend(db_sections)
        return "\n\n".join(sections)

    async def extract_policy_memories(self) -> int:
        """Analyze grounded federal policies, contracts, and budgets for the Catalyst Radar."""
        if not self.client:
            return 0

        grounding_context = await self.fetch_policy_grounding_context()
        if not grounding_context.strip():
            logger.info("Skipping government policy memory extraction: no grounding context available.")
            return 0

        prompt = (
            "Extract ONLY concrete, named US or Canadian government policy shifts, fiscal liquidity signals, "
            "or major procurement catalysts grounded strictly in the verified source material below. "
            "Focus on specific named rules, bills, budgets, energy/critical mineral incentives, infrastructure/defense awards, "
            "or tech/AI regulations. Do NOT invent unverified policies.\n\n"
            f"{grounding_context}"
        )
        try:
            create_call = self.client.chat.completions.create(
                model=GEMINI_MODEL,
                response_model=DecisionsResponse,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a government policy analyst for a hedge fund. "
                            "Synthesize only verifiable catalysts supported by the supplied documents and records. "
                            "Return structured JSON."
                        ),
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
                success = await asyncio.to_thread(
                    add_memory,
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
        except Exception:
            logger.exception("Government policy memory extraction skipped or failed")
            return 0

    async def run(self) -> int:
        """Executes the full government ingestion pipeline."""
        logger.info("Starting Government Pipeline run...")

        # 1. Ingest real macro liquidity (TGA cash balance + national debt)
        try:
            await self.ingest_liquidity()
        except Exception:
            logger.exception("Liquidity ingestion error")

        # 2. Ingest real procurement & contract awards (USAspending + CanadaBuys)
        try:
            await self.ingest_contracts()
        except Exception:
            logger.exception("Contracts ingestion error")

        # 3. Ingest institutional whale stakes (Schedule 13D/13G)
        try:
            await self.ingest_whales()
        except Exception:
            logger.exception("Whale ingestion error")

        # 4. Ingest Congress STOCK Act disclosures
        try:
            await self.ingest_congress()
        except Exception:
            logger.exception("Congress trades ingestion error")

        # 5. Ingest corporate and Canadian insider trades (SEC Form 4s)
        try:
            await self.ingest_insiders()
        except Exception:
            logger.exception("Insider trades ingestion error")

        # 6. Extract policy & incentive memories for catalyst radar
        memories_count = await self.extract_policy_memories()

        logger.info("Government pipeline completed.")
        return memories_count


async def run_government_pipeline() -> dict[str, Any]:
    """Entry point for CLI and scheduled pipeline runs."""
    pipeline = GovernmentPipeline()
    memories_count = await pipeline.run()
    return {"status": "success", "memories_created": memories_count}
