"""Fetchers and database persistence for institutional whale stakes (Schedule 13D/13G).

Tracks:
- Activist blockholder entries (Schedule 13D)
- Major institutional holdings (>5% stakes, Schedule 13G)
- Whale liquidations and exits (stakes dropping to 0%)
"""

from typing import Any

import httpx

from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client

FMP_STABLE_URL = "https://financialmodelingprep.com/stable"
DEFAULT_TIMEOUT = 12.0

# Curated benchmark & high-conviction liquid universe
DEFAULT_WHALE_UNIVERSE = [
    "NVDA",
    "AAPL",
    "MSFT",
    "PLTR",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "AMD",
    "AVGO",
    "LMT",
    "BA",
    "RTX",
    "SHOP",
    "ENB",
    "CCJ",
    "TECK",
]


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "" or str(val).lower() == "null":
        return default
    try:
        clean = str(val).replace("$", "").replace("%", "").replace(",", "").strip()
        return float(clean)
    except (ValueError, TypeError):
        return default


async def fetch_beneficial_ownership(symbol: str) -> list[dict[str, Any]]:
    """Fetch Schedule 13D/13G beneficial ownership disclosures from FMP."""
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY missing, skipping beneficial ownership fetch.")
        return []

    url = f"{FMP_STABLE_URL}/acquisition-of-beneficial-ownership"
    params = {"symbol": symbol.upper().strip(), "apikey": FMP_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
            else:
                logger.warning(
                    "FMP beneficial ownership returned HTTP %d for %s",
                    resp.status_code,
                    symbol,
                )
    except Exception as e:
        logger.warning("Failed fetching beneficial ownership for %s: %s", symbol, e)

    return []


def filter_whale_stakes(
    raw_filings: list[dict[str, Any]],
    min_percent: float = 4.0,
    max_records: int = 50,
) -> list[dict[str, Any]]:
    """Filter raw 13D/13G filings for significant stakes or whale exits."""
    filtered: list[dict[str, Any]] = []

    for item in raw_filings:
        if len(filtered) >= max_records:
            break

        sym = (item.get("symbol") or "").upper().strip()
        filer = (item.get("nameOfReportingPerson") or "").strip()
        f_date = item.get("filingDate")

        if not sym or not filer or not f_date:
            continue

        pct = _safe_float(item.get("percentOfClass"))
        shares = _safe_float(item.get("amountBeneficiallyOwned"))
        url = item.get("url") or ""

        # Flag exits vs accumulation
        is_exit = pct == 0.0 or shares == 0.0
        if not is_exit and pct < min_percent:
            continue

        filing_type = "13D" if "13D" in url.upper() else "13G"

        filtered.append(
            {
                "symbol": sym,
                "filer_name": filer,
                "filer_cik": item.get("cik"),
                "filing_date": f_date[:10],
                "accepted_date": (item.get("acceptedDate") or f_date)[:10],
                "percent_of_class": pct,
                "shares_beneficially_owned": shares,
                "reporting_type": item.get("typeOfReportingPerson") or "UNKNOWN",
                "filing_type": filing_type,
                "is_exit": is_exit,
                "source_url": url,
                "raw_metadata": {
                    "cusip": item.get("cusip"),
                    "citizenship": item.get("citizenshipOrPlaceOfOrganization"),
                },
            }
        )

    return filtered


async def upsert_institutional_whale_stakes(records: list[dict[str, Any]]) -> int:
    """Upsert filtered whale stakes into Supabase/PostgreSQL."""
    if not records:
        return 0
    try:
        sb = get_supabase_client()
        res = (
            sb.table("institutional_whale_stakes")
            .upsert(
                records,
                on_conflict="symbol,filer_name,filing_date,percent_of_class",
            )
            .execute()
        )
        data = getattr(res, "data", None)
        return len(data) if data else len(records)
    except Exception as e:
        logger.error("Failed to upsert institutional_whale_stakes: %s", e)
        return 0


async def ingest_institutional_whales(symbols: list[str] | None = None, min_percent: float = 4.0) -> dict[str, int]:
    """Ingest beneficial ownership stakes for a watchlist into the database."""
    target_symbols = symbols or DEFAULT_WHALE_UNIVERSE
    total_upserted = 0
    symbols_processed = 0

    for sym in target_symbols:
        raw_filings = await fetch_beneficial_ownership(sym)
        if raw_filings:
            valid_stakes = filter_whale_stakes(raw_filings, min_percent=min_percent)
            if valid_stakes:
                count = await upsert_institutional_whale_stakes(valid_stakes)
                total_upserted += count
            symbols_processed += 1

    logger.info(
        "Institutional whale ingestion complete: %d stakes upserted across %d symbols.",
        total_upserted,
        symbols_processed,
    )
    return {
        "symbols_processed": symbols_processed,
        "stakes_upserted": total_upserted,
    }
