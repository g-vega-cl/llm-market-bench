"""Script to calculate daily S&P 500 aggregate valuation and earnings metrics (Market Health Barometer).

This script runs after market close, fetches stock profiles, ratios, analyst estimates,
and earnings history for the top S&P 500 constituents, computes cap-weighted aggregates,
and saves the daily snapshot to Supabase.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from datetime import datetime

import httpx

from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client
from execution.providers.fmp import FMPProvider

# Configuration
CONSTITUENTS_LIMIT = 100  # Top 100 represent ~80% of S&P 500 cap
SEMAPHORE_LIMIT = 4  # Stay well under 300 calls/min limit
FMP_STABLE_URL = "https://financialmodelingprep.com/stable"

# Fallback top 100 S&P 500 constituents by market capitalization
FALLBACK_CONSTITUENTS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
    "GOOG",
    "BRK.B",
    "LLY",
    "AVGO",
    "JPM",
    "TSLA",
    "UNH",
    "XOM",
    "V",
    "MS",
    "PG",
    "MA",
    "COST",
    "JNJ",
    "HD",
    "NFLX",
    "BAC",
    "ABBV",
    "WMT",
    "KO",
    "AMD",
    "MRK",
    "PEP",
    "ORCL",
    "CVX",
    "TMO",
    "ADBE",
    "LIN",
    "PM",
    "CRM",
    "ACN",
    "ABT",
    "GE",
    "QCOM",
    "WFC",
    "INTC",
    "TXN",
    "DIS",
    "CAT",
    "AMGN",
    "AXP",
    "MSI",
    "VZ",
    "HON",
    "IBM",
    "AMAT",
    "BKNG",
    "PLTR",
    "GS",
    "CMCSA",
    "GEV",
    "ISRG",
    "PGR",
    "RTX",
    "TJX",
    "SPGI",
    "UNP",
    "SYK",
    "NOW",
    "LMT",
    "COP",
    "ELV",
    "REGN",
    "VRTX",
    "ANET",
    "SCHW",
    "DE",
    "PANW",
    "MDT",
    "PFE",
    "ETN",
    "BSX",
    "CB",
    "KKR",
    "HCA",
    "MU",
    "MMC",
    "WM",
    "NKE",
    "ADP",
    "PLD",
    "ABNB",
    "CRWD",
    "UPS",
    "LRCX",
    "ADI",
    "MDLZ",
    "PH",
    "MCO",
    "CI",
    "KLAC",
    "T",
    "VLO",
    "EOG",
]


async def fetch_with_retry(
    client: httpx.AsyncClient, url: str, params: dict, semaphore: asyncio.Semaphore, retries: int = 3
) -> list | dict | None:
    """Fetch JSON from FMP API with concurrency limiting and exponential backoff retry."""
    async with semaphore:
        backoff = 1.0
        for attempt in range(retries):
            try:
                # 0.2s polite delay to ensure we don't spam
                await asyncio.sleep(0.2)
                resp = await client.get(url, params=params)

                if resp.status_code == 429:
                    logger.warning(f"FMP Rate Limited (429) on {url}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue

                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"Failed FMP fetch for {url} after {retries} attempts: {e}")
                    return None
                await asyncio.sleep(backoff)
                backoff *= 2
        return None


async def fetch_constituent_data(
    client: httpx.AsyncClient, symbol: str, api_key: str, semaphore: asyncio.Semaphore
) -> dict | None:
    """Fetch all necessary metrics for a single constituent."""
    params = {"symbol": symbol, "apikey": api_key}

    # 1. Fetch profile (market cap, price)
    profile_data = await fetch_with_retry(client, f"{FMP_STABLE_URL}/profile", params, semaphore)
    if not profile_data or not isinstance(profile_data, list) or not profile_data:
        return None
    profile = profile_data[0]

    market_cap = float(profile.get("marketCap") or 0.0)
    price = float(profile.get("price") or 0.0)
    company_name = profile.get("companyName")
    if market_cap <= 0 or price <= 0:
        return None

    # 2. Fetch ratios (pe, pb, ps)
    ratios_data = await fetch_with_retry(
        client,
        f"{FMP_STABLE_URL}/ratios",
        {"symbol": symbol, "period": "annual", "limit": 1, "apikey": api_key},
        semaphore,
    )
    ratios = ratios_data[0] if ratios_data and isinstance(ratios_data, list) else {}

    # 3. Fetch analyst estimates (for forward PE)
    estimates_data = await fetch_with_retry(
        client,
        f"{FMP_STABLE_URL}/analyst-estimates",
        {"symbol": symbol, "period": "annual", "limit": 2, "apikey": api_key},
        semaphore,
    )
    # Get the next fiscal year's EPS estimate
    next_eps_est = None
    if estimates_data and isinstance(estimates_data, list):
        now_year = datetime.now().year
        for est in estimates_data:
            est_date = est.get("date")
            if est_date:
                try:
                    est_year = int(est_date.split("-")[0])
                    if est_year >= now_year:
                        next_eps_est = est.get("epsAvg")
                        break
                except ValueError:
                    pass
        if next_eps_est is None and estimates_data:
            next_eps_est = estimates_data[0].get("epsAvg")

    # 4. Fetch earnings surprises (for beat rate)
    earnings_data = await fetch_with_retry(
        client, f"{FMP_STABLE_URL}/earnings", {"symbol": symbol, "apikey": api_key}, semaphore
    )

    beat = None
    if earnings_data and isinstance(earnings_data, list):
        # Find the most recent completed report (actual eps is not None)
        for earn in earnings_data:
            act = earn.get("epsActual")
            est = earn.get("epsEstimated")
            if act is not None and est is not None and act != "" and est != "":
                try:
                    beat = float(act) > float(est)
                    break
                except ValueError:
                    pass

    return {
        "symbol": symbol,
        "company_name": company_name,
        "market_cap": market_cap,
        "price": price,
        "pe": ratios.get("priceToEarningsRatio"),
        "pb": ratios.get("priceToBookRatio"),
        "ps": ratios.get("priceToSalesRatio"),
        "next_eps_est": next_eps_est,
        "beat": beat,
    }


async def calculate_barometer():
    """Main execution function to calculate S&P 500 barometer."""
    logger.info("Starting S&P 500 Market Health Barometer calculation...")

    if not FMP_API_KEY:
        logger.error("FMP_API_KEY is not set. Barometer calculation aborted.")
        return

    provider = FMPProvider()

    # 1. Fetch S&P 500 constituents dynamically or use fallback
    constituents = await provider.get_sp500_constituents()
    if not constituents:
        logger.warning(f"Using fallback S&P 500 constituents list ({len(FALLBACK_CONSTITUENTS)} symbols).")
        constituents = FALLBACK_CONSTITUENTS
    else:
        logger.info(f"Successfully fetched {len(constituents)} S&P 500 constituents dynamically.")
        constituents = constituents[:CONSTITUENTS_LIMIT]

    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

    async with httpx.AsyncClient() as client:
        tasks = [fetch_constituent_data(client, sym, FMP_API_KEY, semaphore) for sym in constituents]
        results = await asyncio.gather(*tasks)

    # Filter out None values
    valid_results = [r for r in results if r is not None]
    logger.info(f"Retrieved valid valuation data for {len(valid_results)}/{len(constituents)} constituents.")

    if not valid_results:
        logger.error("No valid constituent data retrieved. Skipping update.")
        return

    # 2. Compute cap-weighted aggregates
    # Formula: Index Multiple = Sum(Market Cap) / Sum(Fundamental Value)
    # Fundamental Value = Market Cap / Multiple

    sum_mcap_pe = 0.0
    sum_income = 0.0

    sum_mcap_ps = 0.0
    sum_revenue = 0.0

    sum_mcap_pb = 0.0
    sum_book = 0.0

    sum_mcap_fwd = 0.0
    sum_fwd_income = 0.0

    beats_count = 0
    total_beats_valid = 0

    for r in valid_results:
        mcap = r["market_cap"]

        # Trailing PE / Income
        pe = r["pe"]
        if pe is not None and pe != 0:
            pe_val = float(pe)
            sum_mcap_pe += mcap
            sum_income += mcap / pe_val

        # Price-to-Sales / Revenue
        ps = r["ps"]
        if ps is not None and ps > 0:
            ps_val = float(ps)
            sum_mcap_ps += mcap
            sum_revenue += mcap / ps_val

        # Price-to-Book / Book Value
        pb = r["pb"]
        if pb is not None and pb > 0:
            pb_val = float(pb)
            sum_mcap_pb += mcap
            sum_book += mcap / pb_val

        # Forward PE
        next_eps = r["next_eps_est"]
        if next_eps is not None and r["price"] > 0:
            next_eps_val = float(next_eps)
            # Shares outstanding = Market Cap / Price
            shares = mcap / r["price"]
            fwd_income = next_eps_val * shares
            # We exclude companies with negative/zero estimated EPS for forward income aggregates to keep it clean
            if fwd_income > 0:
                sum_mcap_fwd += mcap
                sum_fwd_income += fwd_income

        # Earnings Beat
        beat = r["beat"]
        if beat is not None:
            total_beats_valid += 1
            if beat:
                beats_count += 1

    # Calculate index-level metrics
    pe_index = (sum_mcap_pe / sum_income) if sum_income != 0 else None
    ps_index = (sum_mcap_ps / sum_revenue) if sum_revenue != 0 else None
    pb_index = (sum_mcap_pb / sum_book) if sum_book != 0 else None
    fwd_pe_index = (sum_mcap_fwd / sum_fwd_income) if sum_fwd_income != 0 else None
    beat_rate = (beats_count / total_beats_valid * 100) if total_beats_valid > 0 else None

    # Construct clean constituents details payload for audit trail
    constituents_payload = []
    for r in valid_results:
        constituents_payload.append({
            "symbol": r["symbol"],
            "company_name": r["company_name"],
            "market_cap": r["market_cap"],
            "price": r["price"],
            "pe": float(r["pe"]) if r["pe"] is not None else None,
            "pb": float(r["pb"]) if r["pb"] is not None else None,
            "ps": float(r["ps"]) if r["ps"] is not None else None,
            "next_eps_est": float(r["next_eps_est"]) if r["next_eps_est"] is not None else None,
            "beat": r["beat"],
        })

    logger.info(
        f"Calculated S&P 500 Aggregates: PE={pe_index}, PS={ps_index}, PB={pb_index}, FwdPE={fwd_pe_index}, BeatRate={beat_rate}"
    )

    # 3. Store to Supabase
    try:
        supabase = get_supabase_client()
        today_str = datetime.now().strftime("%Y-%m-%d")

        payload = {
            "date": today_str,
            "pe_ratio": pe_index,
            "forward_pe": fwd_pe_index,
            "pb_ratio": pb_index,
            "ps_ratio": ps_index,
            "earnings_surprise_momentum": beat_rate,
            "constituents_data": constituents_payload,
            "updated_at": datetime.now().isoformat(),
        }

        supabase.table("market_barometer_history").upsert(payload).execute()
        logger.info(f"S&P 500 Market Health Barometer saved successfully for date {today_str}.")
    except Exception as e:
        logger.exception(f"Failed to save Market Health Barometer to Supabase: {e}")


if __name__ == "__main__":
    asyncio.run(calculate_barometer())
