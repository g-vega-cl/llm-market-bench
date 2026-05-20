import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
"""Utility to rank existing memories by importance using an LLM.

This script iterates through all memories in the database that have a default
importance_score (5) and uses an LLM to assign a more accurate score (1-10).
"""

import asyncio
import logging

from pydantic import BaseModel, Field

from core import config
from core.db import get_supabase_client
from core.llm.clients import get_gemini_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ranker")


class ImportanceRanking(BaseModel):
    importance_score: int = Field(..., ge=1, le=10)
    reasoning: str


async def rank_existing_memories():
    sb_client = get_supabase_client()
    gemini = get_gemini_client()

    # Fetch memories with default importance score
    # We assume 5 is the default from the migration
    response = sb_client.table("memories").select("id", "content").eq("importance_score", 5).execute()
    memories = response.data or []

    logger.info(f"Found {len(memories)} memories to rank.")

    for i, mem in enumerate(memories):
        try:
            prompt = f"""You are a senior financial analyst. Rank the following market event by its intrinsic importance on a scale of 1-10.
            
            10: Major global event (War, Global Pandemic, Financial Crisis, Major Central Bank Policy Shift).
            5: Moderate significance (Earnings of a major company, sector-wide regulatory shift, significant but local economic data).
            1: Minor importance (Incremental update, single stock news, minor analyst rating change).
            
            EVENT:
            {mem["content"]}
            
            Provide the importance score (1-10) and a short reasoning for your choice.
            """

            resp_call = gemini.chat.completions.create(
                model=config.GEMINI_MODEL,
                response_model=ImportanceRanking,
                messages=[
                    {"role": "system", "content": "You are a senior financial analyst."},
                    {"role": "user", "content": prompt},
                ],
            )

            if hasattr(resp_call, "__await__"):
                resp = await resp_call
            else:
                resp = resp_call

            # Update the memory in the database
            sb_client.table("memories").update(
                {
                    "importance_score": resp.importance_score,
                    "metadata": {**mem.get("metadata", {}), "ranking_reasoning": resp.reasoning},
                }
            ).eq("id", mem["id"]).execute()

            logger.info(f"[{i + 1}/{len(memories)}] Ranked memory {mem['id']} as {resp.importance_score}")

        except Exception as e:
            logger.error(f"Failed to rank memory {mem['id']}: {e}")

    logger.info("Ranking process complete.")


if __name__ == "__main__":
    asyncio.run(rank_existing_memories())
