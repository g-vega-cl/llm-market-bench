"""Tool handlers and database pipelines for Corporate Insider trading disclosures (SEC Form 4)."""

import contextlib
from datetime import UTC, datetime, timedelta

import httpx

from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client

FMP_STABLE_URL = "https://financialmodelingprep.com/stable"


def normalize_fmp_insider_trade(raw: dict) -> dict | None:
    """Normalize raw FMP insider trading record to standard schema."""
    if not isinstance(raw, dict):
        return None

    symbol = (raw.get("symbol") or "").strip().upper()
    if not symbol or symbol in {"--", "N/A", "NONE"}:
        return None

    filing_date = raw.get("filingDate")
    transaction_date = raw.get("transactionDate")
    if not filing_date or not transaction_date:
        return None

    # Normalizing dates to YYYY-MM-DD
    filing_date = str(filing_date).split(" ")[0]
    transaction_date = str(transaction_date).split(" ")[0]

    reporting_name = (raw.get("reportingName") or "Unknown Insider").strip()
    owner_type = (raw.get("typeOfOwner") or "").strip()

    raw_tx_type = (raw.get("transactionType") or "").strip().lower()
    if "p-purchase" in raw_tx_type or "buy" in raw_tx_type:
        tx_type = "purchase"
    elif "s-sale" in raw_tx_type or "sale" in raw_tx_type:
        tx_type = "sale"
    else:
        tx_type = "other"

    try:
        shares = float(raw.get("securitiesTransacted") or 0.0)
    except (ValueError, TypeError):
        shares = 0.0

    try:
        price = float(raw.get("price") or 0.0)
    except (ValueError, TypeError):
        price = 0.0

    total_value = round(shares * price, 2)

    try:
        securities_owned = float(raw.get("securitiesOwned")) if raw.get("securitiesOwned") is not None else None
    except (ValueError, TypeError):
        securities_owned = None

    return {
        "symbol": symbol,
        "filing_date": filing_date,
        "transaction_date": transaction_date,
        "reporting_name": reporting_name,
        "type_of_owner": owner_type,
        "transaction_type": tx_type,
        "securities_transacted": shares,
        "price": price,
        "total_value": total_value,
        "securities_owned": securities_owned,
        "source_url": raw.get("url"),
    }


async def fetch_insider_trades_from_fmp(symbol: str, limit: int = 50) -> list[dict]:
    """Fetch recent SEC Form 4 insider trading disclosures from FMP."""
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY missing, skipping insider trades fetch.")
        return []

    url = f"{FMP_STABLE_URL}/insider-trading/search"
    params = {
        "symbol": symbol.upper(),
        "limit": limit,
        "apikey": FMP_API_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning("FMP insider trading search returned HTTP %d", resp.status_code)
                return []

            data = resp.json()
            if not isinstance(data, list):
                return []

            results = []
            for item in data:
                normalized = normalize_fmp_insider_trade(item)
                if normalized:
                    results.append(normalized)
            return results
    except Exception as e:
        logger.warning("Failed to fetch insider trades from FMP: %s", e)
        return []


async def fetch_insider_statistics_from_fmp(symbol: str) -> dict | None:
    """Fetch aggregated quarterly insider trading statistics from FMP."""
    if not FMP_API_KEY:
        return None

    url = f"{FMP_STABLE_URL}/insider-trading/statistics"
    params = {"symbol": symbol.upper(), "apikey": FMP_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0]
            if isinstance(data, dict):
                return data
            return None
    except Exception as e:
        logger.debug("Failed to fetch insider statistics from FMP: %s", e)
        return None


async def upsert_insider_trades_to_db(trades: list[dict]) -> int:
    """Upsert normalized insider trades to Supabase with deduplication."""
    if not trades:
        return 0

    deduped = {}
    for t in trades:
        key = (
            t["symbol"],
            t["reporting_name"],
            t["transaction_date"],
            t["filing_date"],
            t["transaction_type"],
            t["securities_transacted"],
            t["price"],
        )
        deduped[key] = t

    records = list(deduped.values())
    try:
        sb = get_supabase_client()
        resp = (
            sb.table("insider_trades")
            .upsert(
                records,
                on_conflict="symbol,reporting_name,transaction_date,filing_date,transaction_type,securities_transacted,price",
            )
            .execute()
        )
        return len(resp.data or [])
    except Exception as e:
        logger.warning("Failed to upsert insider trades to Supabase: %s", e)
        return 0


async def fetch_insider_trades_from_db(
    symbol: str,
    days: int = 90,
    transaction_type: str | None = None,
    limit: int = 25,
) -> list[dict]:
    """Query recent insider disclosures from Supabase."""
    try:
        sb = get_supabase_client()
        query = sb.table("insider_trades").select("*").eq("symbol", symbol.upper())

        cutoff = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
        query = query.gte("filing_date", cutoff)

        if transaction_type and transaction_type.lower() in {"purchase", "sale"}:
            query = query.eq("transaction_type", transaction_type.lower())

        query = query.order("filing_date", desc=True).limit(limit)
        resp = query.execute()
        return resp.data or []
    except Exception as e:
        logger.warning("Failed to query insider_trades from DB: %s", e)
        return []


async def handle_get_insider_trades(
    symbol: str,
    days: int = 90,
    transaction_type: str = "all",
    limit: int = 15,
) -> str:
    """Format Form 4 insider trading activity for LLM reasoning agents."""
    sym_clean = symbol.strip().upper()
    tx_filter = transaction_type.lower() if transaction_type in {"purchase", "sale"} else None

    trades = await fetch_insider_trades_from_db(
        symbol=sym_clean,
        days=days,
        transaction_type=tx_filter,
        limit=limit,
    )

    if not trades:
        live_trades = await fetch_insider_trades_from_fmp(symbol=sym_clean, limit=50)
        if live_trades:
            with contextlib.suppress(Exception):
                await upsert_insider_trades_to_db(live_trades)

            cutoff = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
            filtered = [t for t in live_trades if t.get("filing_date", "") >= cutoff]
            if tx_filter:
                filtered = [t for t in filtered if t.get("transaction_type") == tx_filter]

            filtered.sort(
                key=lambda x: (x.get("filing_date", ""), x.get("transaction_date", "")),
                reverse=True,
            )
            trades = filtered[:limit]

    if not trades:
        return f"No recent Form 4 insider trading disclosures found for {sym_clean} within the last {days} days."

    total_bought = sum(float(t.get("total_value", 0.0)) for t in trades if t.get("transaction_type") == "purchase")
    total_sold = sum(float(t.get("total_value", 0.0)) for t in trades if t.get("transaction_type") == "sale")
    bought_count = sum(1 for t in trades if t.get("transaction_type") == "purchase")
    sold_count = sum(1 for t in trades if t.get("transaction_type") == "sale")

    if total_bought > total_sold * 1.5 and bought_count > 0:
        sentiment = "Bullish Net Buying by Insiders"
    elif total_sold > total_bought * 1.5 and sold_count > 0:
        sentiment = "Bearish Net Selling / Liquidation by Insiders"
    else:
        sentiment = "Neutral / Mixed Trading Activity"

    stats = await fetch_insider_statistics_from_fmp(sym_clean)
    stats_line = ""
    if stats:
        quarter = f"Q{stats.get('quarter', '')} {stats.get('year', '')}"
        ratio = stats.get("acquiredDisposedRatio", 0.0)
        stats_line = (
            f"Quarterly Benchmark ({quarter}): {stats.get('totalPurchases', 0)} Buys vs "
            f"{stats.get('totalSales', 0)} Sales | Acquired/Disposed Ratio: {ratio:.2f}\n"
        )

    lines = [
        f"### Corporate Insider Trades (SEC Form 4): {sym_clean} (Past {days} Days)",
        f"Tracked Volume: Est. ${total_bought:,.0f} Bought ({bought_count} trades) | Est. ${total_sold:,.0f} Sold ({sold_count} trades)",
        f"Sentiment: {sentiment}",
    ]
    if stats_line:
        lines.append(stats_line.strip())
    lines.extend(
        [
            "",
            "| Insider Name | Title / Role | Action | Shares | Price | Value ($) | Trade Date | Filed |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
    )

    for t in trades[:limit]:
        name = t.get("reporting_name", "Unknown")
        role = t.get("type_of_owner", "Insider")
        if len(role) > 28:
            role = role[:25] + "..."
        action = (t.get("transaction_type") or "").upper()
        try:
            shares = f"{int(float(t.get('securities_transacted') or 0)):,d}"
        except (ValueError, TypeError):
            shares = str(t.get("securities_transacted") or 0)
        price = f"${float(t.get('price') or 0.0):.2f}"
        val = f"${float(t.get('total_value') or 0.0):,.0f}"
        t_date = t.get("transaction_date", "")
        f_date = t.get("filing_date", "")
        lines.append(f"| {name} | {role} | {action} | {shares} | {price} | {val} | {t_date} | {f_date} |")

    return "\n".join(lines)


async def execute_get_insider_trades_tool(
    ticker: str,
    days: int = 90,
    transaction_type: str = "all",
    limit: int = 15,
) -> str:
    """Executes the get_insider_trades tool."""
    return await handle_get_insider_trades(
        symbol=ticker,
        days=days,
        transaction_type=transaction_type,
        limit=limit,
    )
