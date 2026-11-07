"""Congress STOCK Act disclosure fetcher and database persistence.

Fetches Senate and House personal transaction disclosures from FMP,
normalizes disclosures, and upserts them to the `congress_trades` table.
"""

from typing import Any

import httpx

from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client
from tools.congress_tools import (
    FMP_STABLE_URL,
    normalize_fmp_congress_trade,
)


async def fetch_latest_congress_trades(limit: int = 50) -> list[dict[str, Any]]:
    """Fetch recent Congress disclosures across Senate and House."""
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY missing, skipping Congress disclosures fetch.")
        return []

    results: list[dict[str, Any]] = []

    for chamber, endpoint in [("senate", "senate-latest"), ("house", "house-latest")]:
        url = f"{FMP_STABLE_URL}/{endpoint}"
        params = {"apikey": FMP_API_KEY, "limit": str(limit)}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning("FMP %s endpoint returned HTTP %d", endpoint, resp.status_code)
                    continue

                data = resp.json()
                if not isinstance(data, list):
                    continue

                for item in data:
                    normalized = normalize_fmp_congress_trade(item, chamber=chamber)
                    if normalized:
                        results.append(normalized)
        except Exception as e:
            logger.warning("Failed to fetch %s disclosures from FMP: %s", chamber, e)

    return results


async def upsert_congress_trades(records: list[dict[str, Any]]) -> int:
    """Upsert Congress trades to the database with deduplication."""
    if not records:
        return 0

    deduped: dict[tuple, dict[str, Any]] = {}
    for r in records:
        key = (
            r["chamber"],
            r["representative_name"],
            r["symbol"],
            r["transaction_date"],
            r["transaction_type"],
            r["amount_range"],
        )
        deduped[key] = r

    payload = list(deduped.values())
    try:
        sb = get_supabase_client()
        resp = (
            sb.table("congress_trades")
            .upsert(
                payload,
                on_conflict="chamber,representative_name,symbol,transaction_date,transaction_type,amount_range",
            )
            .execute()
        )
        return len(resp.data or [])
    except Exception as e:
        logger.warning("Failed to upsert congress trades: %s", e)
        return 0
