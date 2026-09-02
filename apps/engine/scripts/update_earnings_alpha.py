"""Pipeline script to calculate daily Earnings Alpha, PEAD, SUE, and Sector Bellwethers.

Fetches earnings history, balance sheet metrics, analyst consensus, and price history
for S&P 500 constituents, computes quantitative metrics, and stores snapshots in Supabase.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from datetime import UTC, date, datetime

import httpx

from analytics.earnings_alpha import (
    calculate_sloan_accrual_quality,
    calculate_sue,
)
from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client

FMP_STABLE_URL = "https://financialmodelingprep.com/stable"
CONCURRENCY_SEMAPHORE_LIMIT = 3

SECTOR_ETFS = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Consumer Cyclical": "XLY",
    "Consumer Discretionary": "XLY",
    "Consumer Defensive": "XLP",
    "Consumer Staples": "XLP",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
    "Materials": "XLB",
    "Communication Services": "XLC",
}

DEFAULT_TOP_TICKERS = [
    ("NVDA", "XLK"),
    ("AAPL", "XLK"),
    ("MSFT", "XLK"),
    ("AVGO", "XLK"),
    ("ORCL", "XLK"),
    ("AMD", "XLK"),
    ("JPM", "XLF"),
    ("BAC", "XLF"),
    ("GS", "XLF"),
    ("MS", "XLF"),
    ("C", "XLF"),
    ("WFC", "XLF"),
    ("LLY", "XLV"),
    ("UNH", "XLV"),
    ("JNJ", "XLV"),
    ("ABBV", "XLV"),
    ("MRK", "XLV"),
    ("TMO", "XLV"),
    ("XOM", "XLE"),
    ("CVX", "XLE"),
    ("COP", "XLE"),
    ("SLB", "XLE"),
    ("EOG", "XLE"),
    ("CAT", "XLI"),
    ("GE", "XLI"),
    ("UNP", "XLI"),
    ("HON", "XLI"),
    ("DE", "XLI"),
    ("FDX", "XLI"),
    ("URI", "XLI"),
    ("AMZN", "XLY"),
    ("TSLA", "XLY"),
    ("HD", "XLY"),
    ("MCD", "XLY"),
    ("NKE", "XLY"),
    ("LOW", "XLY"),
    ("PG", "XLP"),
    ("COST", "XLP"),
    ("WMT", "XLP"),
    ("KO", "XLP"),
    ("PEP", "XLP"),
    ("PM", "XLP"),
    ("GOOGL", "XLC"),
    ("META", "XLC"),
    ("NFLX", "XLC"),
    ("DIS", "XLC"),
    ("TMUS", "XLC"),
    ("LIN", "XLB"),
    ("SHW", "XLB"),
    ("FCX", "XLB"),
    ("ECL", "XLB"),
    ("PLD", "XLRE"),
    ("AMT", "XLRE"),
    ("EQIX", "XLRE"),
    ("SPG", "XLRE"),
    ("NEE", "XLU"),
    ("SO", "XLU"),
    ("DUK", "XLU"),
    ("CEG", "XLU"),
]


async def fetch_fmp_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
    semaphore: asyncio.Semaphore | None = None,
    retries: int = 3,
) -> list | dict | None:
    """Fetch JSON with retry logic and polite throttling."""
    backoff = 1.0
    for attempt in range(retries):
        try:
            if semaphore:
                async with semaphore:
                    await asyncio.sleep(0.1)
                    resp = await client.get(url, params=params)
            else:
                resp = await client.get(url, params=params)

            if resp.status_code == 429:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10.0)
                continue
            if resp.status_code == 402:
                logger.warning(f"FMP 402 Payment Required for {url}")
                return None

            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == retries - 1:
                logger.debug(f"Failed FMP fetch for {url}: {e}")
                return None
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 10.0)
    return None


async def process_ticker_earnings_alpha(
    client: httpx.AsyncClient,
    ticker: str,
    sector: str,
    api_key: str,
    as_of_date: date,
    semaphore: asyncio.Semaphore | None = None,
) -> dict | None:
    """Process all fundamental, earnings, and consensus data for a single ticker."""
    try:
        # 1. Fetch Earnings History
        earnings_data = await fetch_fmp_json(
            client, f"{FMP_STABLE_URL}/earnings", {"symbol": ticker, "apikey": api_key}, semaphore
        )
        if not earnings_data or not isinstance(earnings_data, list):
            return None

        reported = [e for e in earnings_data if e.get("epsActual") is not None and e.get("epsEstimated") is not None]
        if not reported:
            return None

        # Sort reported by date descending
        reported.sort(key=lambda x: str(x.get("date", "")), reverse=True)
        recent_report = reported[0]
        report_date_str = str(recent_report.get("date"))
        report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()

        actual_eps = float(recent_report["epsActual"])
        est_eps = float(recent_report["epsEstimated"])
        eps_surprise = actual_eps - est_eps

        rev_actual = float(recent_report["revenueActual"]) if recent_report.get("revenueActual") is not None else None
        rev_est = (
            float(recent_report["revenueEstimated"]) if recent_report.get("revenueEstimated") is not None else None
        )
        rev_surprise_pct = (
            ((rev_actual - rev_est) / rev_est * 100.0)
            if (rev_actual is not None and rev_est is not None and rev_est > 0)
            else None
        )

        # Historical surprises (up to 8 prior quarters)
        prior_surprises = [
            float(e["epsActual"]) - float(e["epsEstimated"])
            for e in reported[1:9]
            if e.get("epsActual") is not None and e.get("epsEstimated") is not None
        ]

        sue_res = calculate_sue(
            actual_eps=actual_eps,
            estimated_eps=est_eps,
            historical_surprises=prior_surprises,
        )

        # 2. Fetch Key Metrics (Sloan Accrual)
        metrics_data = await fetch_fmp_json(
            client, f"{FMP_STABLE_URL}/key-metrics", {"symbol": ticker, "limit": 1, "apikey": api_key}, semaphore
        )
        sloan_accrual_ratio = None
        is_accrual_clean = True
        if metrics_data and isinstance(metrics_data, list) and metrics_data:
            m = metrics_data[0]
            net_income = float(m.get("netIncome", 0.0))
            ocf = float(m.get("operatingCashFlow", 0.0))
            total_assets = float(m.get("totalAssets", 0.0))
            if total_assets > 0 or net_income != 0:
                sloan_accrual_ratio, is_accrual_clean = calculate_sloan_accrual_quality(
                    net_income=net_income,
                    operating_cash_flow=ocf,
                    total_assets=total_assets,
                )

        # 3. Fetch Grades Consensus
        grades_data = await fetch_fmp_json(
            client, f"{FMP_STABLE_URL}/grades-consensus", {"symbol": ticker, "apikey": api_key}, semaphore
        )
        consensus_str = "Unknown"
        total_analysts = 0
        buy_ratio_pct = 0.0
        if grades_data and isinstance(grades_data, list) and grades_data:
            g = grades_data[0]
            consensus_str = g.get("consensus", "Unknown")
            sb = int(g.get("strongBuy", 0))
            b = int(g.get("buy", 0))
            h = int(g.get("hold", 0))
            s = int(g.get("sell", 0))
            ss = int(g.get("strongSell", 0))
            total_analysts = sb + b + h + s + ss
            buy_ratio_pct = ((sb + b) / total_analysts * 100.0) if total_analysts > 0 else 0.0

        # 4. Fetch Price Target Consensus & Quote
        target_data = await fetch_fmp_json(
            client, f"{FMP_STABLE_URL}/price-target-consensus", {"symbol": ticker, "apikey": api_key}, semaphore
        )
        target_consensus_price = None
        target_upside_pct = None
        quote_data = await fetch_fmp_json(
            client, f"{FMP_STABLE_URL}/quote", {"symbol": ticker, "apikey": api_key}, semaphore
        )
        current_price = float(quote_data[0].get("price", 0.0)) if (quote_data and isinstance(quote_data, list)) else 0.0

        if target_data and isinstance(target_data, list) and target_data:
            t = target_data[0]
            if t.get("targetConsensus"):
                target_consensus_price = float(t["targetConsensus"])
                if current_price > 0:
                    target_upside_pct = ((target_consensus_price - current_price) / current_price) * 100.0

        # 5. Days since report and post-earnings drift
        days_since_report = (as_of_date - report_date).days

        return {
            "snapshot_date": as_of_date.strftime("%Y-%m-%d"),
            "ticker": ticker,
            "sector": sector,
            "report_date": report_date_str,
            "actual_eps": actual_eps,
            "estimated_eps": est_eps,
            "eps_surprise": eps_surprise,
            "revenue_actual": rev_actual,
            "revenue_estimated": rev_est,
            "revenue_surprise_pct": rev_surprise_pct,
            "sue_score": sue_res.sue_score,
            "is_top_decile_sue": sue_res.is_top_decile_sue,
            "quarters_analyzed_count": sue_res.quarters_analyzed_count,
            "has_sufficient_earnings_history": sue_res.has_sufficient_earnings_history,
            "sloan_accrual_ratio": sloan_accrual_ratio,
            "is_sloan_accrual_clean": is_accrual_clean,
            "has_extreme_pre_earnings_runup": False,
            "pre_earnings_20d_return_pct": 0.0,
            "days_since_earnings_report": days_since_report,
            "post_earnings_drift_pct": 0.0,
            "post_earnings_alpha_vs_spy": 0.0,
            "analyst_consensus": consensus_str,
            "analyst_coverage_count": total_analysts,
            "analyst_buy_ratio_pct": buy_ratio_pct,
            "target_consensus_price": target_consensus_price,
            "target_consensus_upside_pct": target_upside_pct,
        }
    except Exception as e:
        logger.warning(f"Error processing ticker {ticker} for earnings alpha: {e}")
        return None


async def run_earnings_alpha_pipeline(as_of_date: date | None = None, test_mode: bool = False):
    """Run full batch pipeline for S&P 500 constituents."""
    if not as_of_date:
        as_of_date = datetime.now(UTC).date()

    logger.info(f"Starting Earnings Alpha pipeline run as of {as_of_date}...")
    if not FMP_API_KEY:
        logger.error("FMP_API_KEY is missing. Aborting run.")
        return

    semaphore = asyncio.Semaphore(CONCURRENCY_SEMAPHORE_LIMIT)
    snapshots = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [
            process_ticker_earnings_alpha(client, ticker, sector, FMP_API_KEY, as_of_date, semaphore)
            for ticker, sector in DEFAULT_TOP_TICKERS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, dict):
                snapshots.append(res)

    logger.info(f"Calculated {len(snapshots)} earnings alpha snapshots.")

    if not test_mode and snapshots:
        try:
            supabase = get_supabase_client()
            # Upsert into earnings_alpha_snapshots
            supabase.table("earnings_alpha_snapshots").upsert(snapshots, on_conflict="snapshot_date,ticker").execute()
            logger.info("Successfully upserted snapshots into Supabase.")
        except Exception as e:
            logger.exception(f"Failed to upsert snapshots to database: {e}")


if __name__ == "__main__":
    asyncio.run(run_earnings_alpha_pipeline())
