"""Corporate & Canadian insider trading fetcher and database persistence.

Fetches SEC Form 4 filings and dual-listed Canadian insider activity from FMP,
normalizes transactions, and upserts them to the `insider_trades` table.
"""

import asyncio
from typing import Any

import httpx

from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client
from tools.insider_tools import (
    FMP_STABLE_URL,
    normalize_fmp_insider_trade,
)

# High-priority active universe, including prominent Canadian dual-listed bellwethers
CANADIAN_AND_CORE_UNIVERSE = [
    # Prominent Canadian bellwethers (TSX / US dual-listed)
    "SHOP",
    "SU",
    "ENB",
    "RY",
    "TD",
    "CNR",
    "CP",
    "BMO",
    "BNS",
    "MFC",
    "BCE",
    "WCN",
    "OTEX",
    "NTR",
    "FNV",
    "AGI",
    # Core mega-caps & volatile catalysts
    "NVDA",
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "PLTR",
    "AMD",
    "AVGO",
]


async def fetch_latest_insider_trades(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch market-wide latest SEC Form 4 insider trading disclosures."""
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY missing, skipping latest insider trades fetch.")
        return []

    url = f"{FMP_STABLE_URL}/insider-trading/latest"
    params = {"apikey": FMP_API_KEY, "limit": str(limit)}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning("FMP insider-trading/latest returned HTTP %d", resp.status_code)
                return []

            data = resp.json()
            if not isinstance(data, list):
                return []

            results: list[dict[str, Any]] = []
            for item in data:
                normalized = normalize_fmp_insider_trade(item)
                if normalized:
                    results.append(normalized)
            return results
    except Exception as e:
        logger.warning("Failed to fetch latest insider trades from FMP: %s", e)
        return []


async def fetch_universe_insider_trades(
    symbols: list[str] | None = None,
    limit_per_symbol: int = 25,
) -> list[dict[str, Any]]:
    """Fetch recent insider transactions for active universe & Canadian bellwethers."""
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY missing, skipping universe insider trades fetch.")
        return []

    target_symbols = symbols or CANADIAN_AND_CORE_UNIVERSE
    results: list[dict[str, Any]] = []

    async def _fetch_symbol(client: httpx.AsyncClient, sym: str) -> list[dict[str, Any]]:
        url = f"{FMP_STABLE_URL}/insider-trading/search"
        params = {
            "symbol": sym.upper(),
            "limit": str(limit_per_symbol),
            "apikey": FMP_API_KEY,
        }
        try:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return []

            data = resp.json()
            if not isinstance(data, list):
                return []

            return [normalized for item in data if (normalized := normalize_fmp_insider_trade(item))]
        except Exception as sym_err:
            logger.debug("Failed fetching insider trades for %s: %s", sym, sym_err)
            return []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            nested = await asyncio.gather(*[_fetch_symbol(client, s) for s in target_symbols])
            for batch in nested:
                results.extend(batch)
    except Exception as e:
        logger.warning("Error during universe insider trades scan: %s", e)

    return results


async def upsert_insider_trades(records: list[dict[str, Any]]) -> int:
    """Upsert insider trades to the database with deduplication."""
    if not records:
        return 0

    deduped: dict[tuple, dict[str, Any]] = {}
    for r in records:
        key = (
            r["symbol"],
            r["reporting_name"],
            r["transaction_date"],
            r["filing_date"],
            r["transaction_type"],
            r["securities_transacted"],
            r["price"],
        )
        deduped[key] = r

    payload = list(deduped.values())
    try:
        sb = get_supabase_client()
        resp = (
            sb.table("insider_trades")
            .upsert(
                payload,
                on_conflict="symbol,reporting_name,transaction_date,filing_date,transaction_type,securities_transacted,price",
            )
            .execute()
        )
        return len(resp.data or [])
    except Exception as e:
        logger.warning("Failed to upsert insider trades: %s", e)
        return 0
