"""Standalone script to compute rolling correlation matrix for uncorrelated asset discovery.

This script runs weekly (Sundays 16:00 ET via GitHub Actions) and:
1. Fetches 90 days of EOD price data for all tickers in the universe
2. Calculates Pearson and Spearman correlation matrices
3. Stores results in Supabase for the Market Overview page and AI agents

Usage:
    python correlation_matrix.py
"""

import asyncio
import json
import sys
import os
# Add the engine root directory to path for sibling package imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from datetime import datetime, timezone
from typing import Optional

from scipy import stats

from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client
from execution.providers.fmp import FMPProvider


# =============================================================================
# TICKER UNIVERSE
# =============================================================================

TICKER_UNIVERSE = [
    # US Sectors (14)
    "XLK", "SMH", "XLE", "XLF", "XLV", "XLY", "XLI", "XLB", "XLU", "XLRE", "XLC",
    "XOP", "XME", "XBI",
    # US Sub-Sectors (3)
    "KRE", "XRT", "XHB",
    # US Broad (4)
    "QQQ", "VIG", "IWM", "SPY",
    # International Developed (8)
    "EFA", "EWJ", "EWG", "EWL", "EWP", "SCZ", "BWX", "EWA",
    # Emerging Markets (6)
    "EEM", "MCHI", "EWZ", "EIDO", "EPI", "INDA",
    # Commodities (7)
    "GLD", "SLV", "PDBC", "USO", "CPER", "UNG", "DBA",
    # Bonds (6)
    "TLT", "IEF", "LQD", "EMB", "HYG", "AGG",
    # International Bonds (3)
    "BNDX", "IAGG", "EMLC",
    # Real Assets (2)
    "VNQ", "ICF",
    # Dollar (1)
    "UUP",
    # Crypto (2) - FMP uses BTCUSD/ETHUSD format
    "BTCUSD", "ETHUSD",
    # Volatility (2)
    "VIXY", "VIXM",
]

WINDOW_DAYS = 90
SMA_WINDOW = 5  # days for smoothing endpoints in 90d return calc


# =============================================================================
# DATA FETCHING
# =============================================================================

async def fetch_ticker_history(provider: FMPProvider, ticker: str, days: int) -> Optional[list[float]]:
    """Fetch historical close prices for a ticker.

    Returns:
        List of closing prices (oldest first) or None if fetch failed.
    """
    history = await provider.get_history(ticker, days=days)

    if not history:
        logger.warning(f"No history found for {ticker}")
        return None

    # Sort by date (oldest first)
    sorted_history = sorted(history, key=lambda x: x["fetched_at"])
    prices = [entry["price"] for entry in sorted_history]

    logger.info(f"Fetched {len(prices)} price points for {ticker}")
    return prices


async def fetch_all_prices(tickers: list[str], days: int) -> dict[str, list[float]]:
    """Fetch historical prices for all tickers.

    Returns:
        Dictionary mapping ticker -> list of prices (oldest first).
        Excludes tickers that failed to fetch.
    """
    provider = FMPProvider()
    results = {}

    # Fetch all tickers in parallel with semaphore to limit concurrency
    semaphore = asyncio.Semaphore(10)

    async def fetch_one(ticker: str) -> tuple[str, Optional[list[float]]]:
        async with semaphore:
            prices = await fetch_ticker_history(provider, ticker, days)
            return ticker, prices

    tasks = [fetch_one(t) for t in tickers]
    task_results = await asyncio.gather(*tasks)

    for ticker, prices in task_results:
        if prices is not None and len(prices) >= 30:  # Require at least 30 days of data
            results[ticker] = prices
        else:
            logger.warning(f"Excluding {ticker}: insufficient data ({len(prices) if prices else 0} points)")

    return results


# =============================================================================
# CORRELATION CALCULATION
# =============================================================================

def compute_returns(prices: list[float]) -> np.ndarray:
    """Calculate daily percentage returns.

    Args:
        prices: List of prices (oldest first).

    Returns:
        Array of daily returns (skipping first entry since no return for day 0).
    """
    return np.diff(prices) / np.array(prices[:-1])


def compute_correlation_matrices(
    returns_dict: dict[str, list[float]]
) -> tuple[dict, dict]:
    """Compute Pearson and Spearman correlation matrices.

    Args:
        returns_dict: Dictionary mapping ticker -> list of returns.

    Returns:
        Tuple of (pearson_matrix, spearman_matrix) as dicts keyed by (ticker_a, ticker_b).
    """
    tickers = list(returns_dict.keys())
    n = len(tickers)

    # Find minimum length across all tickers to ensure alignment
    min_length = min(len(returns_dict[t]) for t in tickers)

    # Build returns matrix with aligned lengths (rows = tickers, columns = time points)
    # Truncate all to minimum length
    returns_matrix = np.array([returns_dict[t][:min_length] for t in tickers])

    pearson_correlations = {}
    spearman_correlations = {}

    for i in range(n):
        for j in range(i + 1, n):
            ticker_a = tickers[i]
            ticker_b = tickers[j]

            returns_a = returns_matrix[i]
            returns_b = returns_matrix[j]

            # Align lengths (some tickers may have slightly different lengths)
            min_len = min(len(returns_a), len(returns_b))
            if min_len < 30:
                logger.warning(f"Skipping {ticker_a}/{ticker_b}: only {min_len} aligned observations")
                continue

            returns_a_aligned = returns_a[:min_len]
            returns_b_aligned = returns_b[:min_len]

            # Pearson correlation
            pearson_corr, _ = stats.pearsonr(returns_a_aligned, returns_b_aligned)

            # Spearman correlation
            spearman_corr, _ = stats.spearmanr(returns_a_aligned, returns_b_aligned)

            key = (ticker_a, ticker_b)
            pearson_correlations[key] = float(pearson_corr)
            spearman_correlations[key] = float(spearman_corr)

    return pearson_correlations, spearman_correlations


def compute_90d_returns(prices_dict: dict[str, list[float]]) -> dict[str, float]:
    """Compute 90-day total returns for each ticker.

    Uses a {SMA_WINDOW}-day simple moving average at both endpoints to reduce
    daily-volatility influence on the starting/ending prices. Falls back to the
    raw endpoint method when fewer than {SMA_WINDOW * 2} price points are available.

    Args:
        prices_dict: Dictionary mapping ticker -> list of prices (oldest first).

    Returns:
        Dictionary mapping ticker -> 90-day return as percentage.
    """
    returns = {}
    min_for_sma = SMA_WINDOW * 2
    for ticker, prices in prices_dict.items():
        if len(prices) < 2:
            continue

        if len(prices) >= min_for_sma:
            start_sma = sum(prices[:SMA_WINDOW]) / SMA_WINDOW
            end_sma = sum(prices[-SMA_WINDOW:]) / SMA_WINDOW
            total_return = ((end_sma / start_sma) - 1) * 100
        else:
            total_return = ((prices[-1] / prices[0]) - 1) * 100

        returns[ticker] = float(total_return)
    return returns


# =============================================================================
# DATABASE STORAGE
# =============================================================================

def store_correlation_results(
    client,
    tickers: list[str],
    pearson_corrs: dict,
    spearman_corrs: dict,
    returns_90d: dict,
    window_days: int = 90
) -> str:
    """Store correlation results to Supabase.

    Args:
        client: Supabase client.
        tickers: List of all tickers included in the computation.
        pearson_corrs: Dict of (ticker_a, ticker_b) -> pearson correlation.
        spearman_corrs: Dict of (ticker_a, ticker_b) -> spearman correlation.
        returns_90d: Dict of ticker -> 90-day return percentage.
        window_days: Rolling window used for computation.

    Returns:
        The run_id (UUID) of the created correlation run.
    """
    from supabase import Client

    # Get today's date (Sunday)
    today = datetime.now(timezone.utc).date()
    run_date = today.isoformat()

    # Check if we already have a run for this date
    existing = client.table("correlation_runs").select("id").eq("run_date", run_date).execute()
    if existing.data:
        logger.info(f"Deleting existing run for {run_date}")
        client.table("correlation_runs").delete().eq("id", existing.data[0]["id"]).execute()

    # Insert correlation run record
    run_data = {
        "run_date": run_date,
        "window_days": window_days,
        "num_assets": len(tickers),
        "tickers": tickers,
    }

    run_response = client.table("correlation_runs").insert(run_data).execute()
    run_id = run_response.data[0]["id"]

    logger.info(f"Created correlation run {run_id} for {run_date} with {len(tickers)} assets")

    # Build list of correlation_data records
    correlation_records = []
    for (ticker_a, ticker_b), pearson_corr in pearson_corrs.items():
        spearman_corr = spearman_corrs.get((ticker_a, ticker_b), None)
        returns_a = returns_90d.get(ticker_a, None)
        returns_b = returns_90d.get(ticker_b, None)

        correlation_records.append({
            "run_id": run_id,
            "ticker_a": ticker_a,
            "ticker_b": ticker_b,
            "pearson_corr": pearson_corr,
            "spearman_corr": spearman_corr,
            "returns_a_90d": returns_a,
            "returns_b_90d": returns_b,
            "data_points": window_days,
        })

    # Batch insert correlation data
    if correlation_records:
        # Insert in batches of 500
        batch_size = 500
        for i in range(0, len(correlation_records), batch_size):
            batch = correlation_records[i:i + batch_size]
            client.table("correlation_data").insert(batch).execute()
            logger.info(f"Inserted batch {i // batch_size + 1} ({len(batch)} records)")

    logger.info(f"Stored {len(correlation_records)} correlation pairs")

    return run_id


# =============================================================================
# TICKER VERIFICATION
# =============================================================================

async def verify_tickers(provider: FMPProvider, tickers: list[str]) -> tuple[list[str], list[str]]:
    """Verify which tickers are available on FMP.

    Args:
        provider: FMPProvider instance.
        tickers: List of tickers to verify.

    Returns:
        Tuple of (valid_tickers, failed_tickers).
    """
    valid = []
    failed = []

    for ticker in tickers:
        history = await provider.get_history(ticker, days=5)  # Just fetch 5 days for verification
        if history and len(history) >= 2:
            valid.append(ticker)
            logger.info(f"Verified: {ticker} ({len(history)} data points)")
        else:
            failed.append(ticker)
            logger.warning(f"Failed verification: {ticker}")

    return valid, failed


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main correlation matrix computation."""
    logger.info("=" * 60)
    logger.info("Starting Correlation Matrix Computation")
    logger.info("=" * 60)

    # Check FMP API key
    if not FMP_API_KEY:
        logger.error("FMP_API_KEY not found in environment")
        sys.exit(1)

    # Initialize Supabase client
    try:
        client = get_supabase_client()
        logger.info("Connected to Supabase")
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        sys.exit(1)

    # First, verify tickers exist on FMP
    logger.info("Verifying tickers on FMP...")
    provider = FMPProvider()

    # We need to verify each ticker
    valid_tickers = []
    failed_tickers = []

    for ticker in TICKER_UNIVERSE:
        history = await provider.get_history(ticker, days=5)
        if history and len(history) >= 2:
            valid_tickers.append(ticker)
            logger.info(f"  OK: {ticker}")
        else:
            failed_tickers.append(ticker)
            logger.warning(f"  FAIL: {ticker} - insufficient data")

    logger.info(f"\nVerification complete:")
    logger.info(f"  Valid tickers: {len(valid_tickers)}")
    logger.info(f"  Failed tickers: {len(failed_tickers)}")

    if failed_tickers:
        logger.warning(f"  Removing failed tickers: {failed_tickers}")

    if not valid_tickers:
        logger.error("No valid tickers found. Aborting.")
        sys.exit(1)

    # Fetch historical data for valid tickers
    logger.info(f"\nFetching {WINDOW_DAYS} days of historical data for {len(valid_tickers)} tickers...")
    prices = await fetch_all_prices(valid_tickers, days=WINDOW_DAYS)

    logger.info(f"Successfully fetched data for {len(prices)} tickers")

    if len(prices) < 2:
        logger.error("Need at least 2 tickers to compute correlations. Aborting.")
        sys.exit(1)

    # Calculate returns
    logger.info("\nComputing daily returns...")
    returns_dict = {}
    for ticker, price_list in prices.items():
        returns = compute_returns(price_list)
        if len(returns) >= 30:
            returns_dict[ticker] = returns
        else:
            logger.warning(f"Excluding {ticker}: only {len(returns)} return observations")

    logger.info(f"Computing correlations for {len(returns_dict)} tickers...")

    # Compute correlation matrices
    pearson_corrs, spearman_corrs = compute_correlation_matrices(returns_dict)

    # Compute 90-day returns
    returns_90d = compute_90d_returns(prices)

    # Store results
    logger.info("\nStoring results to Supabase...")
    run_id = store_correlation_results(
        client,
        list(returns_dict.keys()),
        pearson_corrs,
        spearman_corrs,
        returns_90d,
        window_days=WINDOW_DAYS
    )

    # Verify storage integrity
    try:
        stored_count_response = client.table("correlation_data").select("id", count="exact").eq("run_id", run_id).execute()
        stored_count = stored_count_response.count
        expected_count = len(pearson_corrs)

        if stored_count is not None and stored_count != expected_count:
            logger.error(
                f"Storage verification failed: expected {expected_count} correlation records, "
                f"but found {stored_count} in the database for run_id {run_id}."
            )
            sys.exit(1)

        if stored_count is None:
            logger.warning("Could not verify stored row count (count returned None). Proceeding anyway.")
        else:
            logger.info(f"Storage verification passed: {stored_count} correlation records persisted.")
    except Exception as e:
        logger.error(f"Storage verification query failed: {e}")
        sys.exit(1)

    logger.info(f"\nCorrelation matrix computation complete!")
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Total pairs computed: {len(pearson_corrs)}")

    # Log some summary statistics
    if pearson_corrs:
        corr_values = list(pearson_corrs.values())
        logger.info(f"\nPearson correlation stats:")
        logger.info(f"  Min:  {min(corr_values):.4f}")
        logger.info(f"  Max:  {max(corr_values):.4f}")
        logger.info(f"  Mean: {np.mean(corr_values):.4f}")

        # Find most uncorrelated pairs (closest to 0)
        uncorrelated = sorted(pearson_corrs.items(), key=lambda x: abs(x[1]))[:5]
        logger.info(f"\nMost uncorrelated pairs:")
        for (a, b), corr in uncorrelated:
            r_a = returns_90d.get(a, 0)
            r_b = returns_90d.get(b, 0)
            logger.info(f"  {a}/{b}: {corr:.4f} (90d returns: {r_a:.2f}%, {r_b:.2f}%)")


if __name__ == "__main__":
    asyncio.run(main())
