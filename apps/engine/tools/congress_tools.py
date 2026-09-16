"""Tool handlers and database pipelines for Congress trading disclosures."""

import contextlib
import re
from datetime import UTC, datetime, timedelta

import httpx

from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client

FMP_STABLE_URL = "https://financialmodelingprep.com/stable"


def parse_amount_range_to_midpoint(amount_str: str | None) -> float:
    """Parse a disclosure amount tier range into a numeric midpoint estimate.

    Examples:
        '$1,001 - $15,000' -> 8000.50
        '> $50,000,000' -> 50000000.00
    """
    if not amount_str or not isinstance(amount_str, str):
        return 0.0

    cleaned = amount_str.replace("$", "").replace(",", "").strip()
    if not cleaned:
        return 0.0

    if ">" in cleaned or "+" in cleaned:
        digits = re.findall(r"\d+", cleaned)
        if digits:
            return float("".join(digits))
        return 0.0

    if "-" in cleaned:
        parts = cleaned.split("-")
        if len(parts) == 2:
            try:
                low = float(parts[0].strip())
                high = float(parts[1].strip())
                return round((low + high) / 2.0, 2)
            except ValueError:
                pass

    digits = re.findall(r"\d+", cleaned)
    if digits:
        try:
            return float("".join(digits))
        except ValueError:
            return 0.0

    return 0.0


def normalize_fmp_congress_trade(raw: dict, chamber: str) -> dict | None:
    """Normalize raw FMP Senate or House dictionary to Supabase record format."""
    if not isinstance(raw, dict):
        return None

    symbol = (raw.get("symbol") or "").strip().upper()
    if not symbol or symbol in {"--", "N/A", "NONE"}:
        return None

    transaction_date = raw.get("transactionDate")
    disclosure_date = raw.get("disclosureDate")
    if not transaction_date or not disclosure_date:
        return None

    first_name = (raw.get("firstName") or "").strip()
    last_name = (raw.get("lastName") or "").strip()
    rep_name = f"{first_name} {last_name}".strip()
    if not rep_name:
        rep_name = (raw.get("office") or "Unknown Member").strip()

    raw_type = (raw.get("type") or "").strip().lower()
    if "purchase" in raw_type or "buy" in raw_type:
        tx_type = "purchase"
    elif "sale" in raw_type or "sold" in raw_type:
        tx_type = "sale"
    elif "exchange" in raw_type:
        tx_type = "exchange"
    else:
        tx_type = "purchase"

    amount_range = (raw.get("amount") or "$1,001 - $15,000").strip()
    midpoint = parse_amount_range_to_midpoint(amount_range)

    return {
        "chamber": chamber.lower(),
        "symbol": symbol,
        "transaction_date": transaction_date,
        "disclosure_date": disclosure_date,
        "representative_name": rep_name,
        "district": raw.get("district"),
        "owner": raw.get("owner"),
        "transaction_type": tx_type,
        "amount_range": amount_range,
        "amount_est_midpoint": midpoint,
        "asset_description": raw.get("assetDescription"),
        "source_url": raw.get("link"),
    }


async def fetch_congress_trades_from_fmp(chamber: str, symbol: str | None = None) -> list[dict]:
    """Fetch recent Congress disclosures from FMP for House or Senate."""
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY missing, skipping Congress trades fetch.")
        return []

    chamber_clean = chamber.lower()
    if chamber_clean == "senate":
        endpoint = "senate-trades" if symbol else "senate-latest"
    elif chamber_clean == "house":
        endpoint = "house-trades" if symbol else "house-latest"
    else:
        logger.warning(f"Unknown chamber: {chamber}")
        return []

    url = f"{FMP_STABLE_URL}/{endpoint}"
    params: dict[str, str] = {"apikey": FMP_API_KEY}
    if symbol:
        params["symbol"] = symbol.upper()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"FMP Congress endpoint {endpoint} returned status {resp.status_code}")
                return []

            data = resp.json()
            if not isinstance(data, list):
                return []

            results = []
            for item in data:
                normalized = normalize_fmp_congress_trade(item, chamber=chamber_clean)
                if normalized:
                    results.append(normalized)
            return results
    except Exception as e:
        logger.warning(f"Failed to fetch Congress trades from FMP: {e}")
        return []


async def upsert_congress_trades_to_db(trades: list[dict]) -> int:
    """Upsert normalized Congress trades to Supabase with deduplication."""
    if not trades:
        return 0

    deduped: dict[tuple, dict] = {}
    for t in trades:
        key = (
            t["chamber"],
            t["representative_name"],
            t["symbol"],
            t["transaction_date"],
            t["transaction_type"],
            t["amount_range"],
        )
        deduped[key] = t

    records = list(deduped.values())
    try:
        sb = get_supabase_client()
        resp = sb.table("congress_trades").upsert(
            records,
            on_conflict="chamber,representative_name,symbol,transaction_date,transaction_type,amount_range",
        ).execute()
        return len(resp.data or [])
    except Exception as e:
        logger.warning(f"Failed to upsert Congress trades to Supabase: {e}")
        return 0


async def fetch_congress_trades_from_db(
    symbol: str | None = None,
    chamber: str | None = None,
    days: int = 30,
    transaction_type: str | None = None,
    limit: int = 25,
) -> list[dict]:
    """Query recent Congress disclosures from Supabase."""
    try:
        sb = get_supabase_client()
        query = sb.table("congress_trades").select("*")

        cutoff = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
        query = query.gte("disclosure_date", cutoff)

        if symbol:
            query = query.eq("symbol", symbol.upper())
        if chamber:
            query = query.eq("chamber", chamber.lower())
        if transaction_type:
            query = query.eq("transaction_type", transaction_type.lower())

        query = query.order("disclosure_date", desc=True).limit(limit)
        resp = query.execute()
        return resp.data or []
    except Exception as e:
        logger.warning(f"Failed to query congress_trades from DB: {e}")
        return []


async def handle_get_congress_trades(
    symbol: str | None = None,
    chamber: str | None = None,
    days: int = 45,
    transaction_type: str | None = None,
    limit: int = 20,
) -> str:
    """Format Congress trading activity for LLM reasoning agents."""
    trades = await fetch_congress_trades_from_db(
        symbol=symbol,
        chamber=chamber,
        days=days,
        transaction_type=transaction_type,
        limit=limit,
    )

    if not trades:
        senate_trades = await fetch_congress_trades_from_fmp(chamber="senate", symbol=symbol)
        house_trades = await fetch_congress_trades_from_fmp(chamber="house", symbol=symbol)
        combined = senate_trades + house_trades
        if combined:
            with contextlib.suppress(Exception):
                await upsert_congress_trades_to_db(combined)

            cutoff = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
            filtered = [t for t in combined if t.get("disclosure_date", "") >= cutoff]
            if transaction_type:
                filtered = [t for t in filtered if t.get("transaction_type") == transaction_type.lower()]
            if chamber:
                filtered = [t for t in filtered if t.get("chamber") == chamber.lower()]

            filtered.sort(
                key=lambda x: (x.get("disclosure_date", ""), x.get("transaction_date", "")),
                reverse=True,
            )
            trades = filtered[:limit]

    if not trades:
        target = f"for {symbol.upper()}" if symbol else "in the specified window"
        return f"No recent Congress trading disclosures found {target} within the last {days} days."

    total_bought_est = sum(
        t.get("amount_est_midpoint", 0.0) for t in trades if t.get("transaction_type") == "purchase"
    )
    total_sold_est = sum(
        t.get("amount_est_midpoint", 0.0) for t in trades if t.get("transaction_type") == "sale"
    )

    lines = [
        f"### Congress Trading Disclosures (Past {days} Days)",
        f"Total Tracked Volume: Est. ${total_bought_est:,.0f} Bought | Est. ${total_sold_est:,.0f} Sold",
        "",
        "| Chamber | Member | District | Symbol | Type | Range | Traded | Disclosed |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for t in trades[:limit]:
        cham = t.get("chamber", "").capitalize()
        name = t.get("representative_name", "Unknown")
        dist = t.get("district") or "-"
        sym = t.get("symbol", "")
        action = (t.get("transaction_type") or "").upper()
        amt = t.get("amount_range", "")
        tx_d = t.get("transaction_date", "")
        disc_d = t.get("disclosure_date", "")
        lines.append(f"| {cham} | {name} | {dist} | {sym} | {action} | {amt} | {tx_d} | {disc_d} |")

    return "\n".join(lines)
