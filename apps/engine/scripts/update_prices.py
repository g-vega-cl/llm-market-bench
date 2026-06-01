"""Script to update market prices and recalculate portfolio metrics without LLM calls."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import math

from core.config import logger
from core.db import SUPABASE_RETRIES, get_supabase_client, is_transient_supabase_error
from execution.market_data import MarketDataManager
from execution.portfolio import Portfolio

BENCHMARK_TICKERS = [
    "SPY",
    "QQQ",
    "GLD",
    "VGK",
    "EWJ",
    "EEM",
    "IWM",
    "DIA",
    "URTH",
    "TLT",
    "TIP",
    "UNG",
    "BTCUSD",
    "EWU",
    "EWC",
    "CPER",
]
BENCHMARK_HISTORY_DAYS = 90


async def initialize_with_retry(owner: str) -> Portfolio:
    """Initialize a portfolio with retry logic for transient Supabase errors."""
    p = Portfolio(owner_id=owner)

    for attempt in range(1, SUPABASE_RETRIES + 1):
        try:
            await p.initialize()
            return p
        except Exception as exc:
            if not is_transient_supabase_error(exc):
                logger.error(f"initialize_portfolio({owner}) failed with non-transient error: {exc}")
                raise

            if attempt < SUPABASE_RETRIES:
                wait_time = 2 ** (attempt - 1)
                logger.warning(
                    f"initialize_portfolio({owner}) failed (attempt {attempt}/{SUPABASE_RETRIES}), "
                    f"retrying in {wait_time}s. Error: {exc}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"initialize_portfolio({owner}) failed after {SUPABASE_RETRIES} attempts: {exc}")
                raise

    return p


async def update_prices():
    """Main function to update prices and metrics."""
    logger.info("Starting Price Update Script (No LLM)...")

    sb_client = get_supabase_client()
    mdm = MarketDataManager()

    # 0. Check if market is open
    if not await mdm.is_market_open():
        logger.info("Market is currently CLOSED. Skipping price update to save resources.")
        return

    # 1. Get all active portfolios
    def fetch_portfolios():
        return sb_client.table("portfolios").select("owner_id").execute()

    for attempt in range(1, SUPABASE_RETRIES + 1):
        try:
            port_res = fetch_portfolios()
            owners = [p["owner_id"] for p in port_res.data] if port_res.data else []
            break
        except Exception as exc:
            if not is_transient_supabase_error(exc):
                logger.error(f"fetch_portfolios failed with non-transient error: {exc}")
                raise
            if attempt < SUPABASE_RETRIES:
                wait_time = 2 ** (attempt - 1)
                logger.warning(
                    f"fetch_portfolios failed (attempt {attempt}/{SUPABASE_RETRIES}), "
                    f"retrying in {wait_time}s. Error: {exc}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Failed to fetch portfolios after {SUPABASE_RETRIES} attempts: {exc}")
                return

    if not owners:
        logger.warning("No portfolios found to update.")
        return

    logger.info(f"Found {len(owners)} portfolios to update.")

    # 2. Collect all unique tickers across all portfolios
    all_tickers = set()
    portfolios_to_update = []

    for owner in owners:
        try:
            p = await initialize_with_retry(owner)
            all_tickers.update(p.positions.keys())
            portfolios_to_update.append(p)
        except Exception as e:
            logger.error(f"Failed to initialize portfolio {owner}: {e}")
            continue

    logger.info(f"Identified {len(all_tickers)} unique tickers: {all_tickers}")

    # 3. Fetch fresh prices for all tickers in batch
    logger.info(f"Fetching fresh quotes for {len(all_tickers)} tickers in batch...")
    # Force refresh to ensure we get the latest prices
    prices = await mdm.get_quotes(list(all_tickers), force_refresh=True)

    price_map = {t: data.price for t, data in prices.items()}

    for ticker in all_tickers:
        if ticker in price_map:
            logger.info(f"Updated price for {ticker}: ${price_map[ticker]:.2f}")
        else:
            logger.warning(f"Could not fetch price for {ticker}. Using fallback if available.")

    # 4. Update metrics and record snapshots for each portfolio
    updated_count = 0
    for p in portfolios_to_update:
        try:
            # We need to ensure we have prices for at least the positions held
            # calculate_reg_t_metrics will handle missing prices by using ACB (see Guardrail E in Overview)

            logger.info(f"Recalculating metrics for portfolio: {p.owner_id}")
            p.calculate_reg_t_metrics(price_map)

            # Persist updated metrics to main portfolios table
            await p.save_metrics()

            # Record daily performance snapshot
            await p.record_performance_snapshot(price_map)

            updated_count += 1
            logger.info(f"Successfully updated {p.owner_id}.")
        except Exception as e:
            logger.error(f"Error updating portfolio {p.owner_id}: {e}")

    logger.info(f"Price update complete. Updated {updated_count} portfolios.")

    # 5. Fetch and store benchmark ticker history
    await fetch_benchmark_history(mdm)


async def fetch_benchmark_history(mdm: MarketDataManager):
    """Fetch 90-day history for benchmark tickers and macro tickers, and store in price_history table."""
    from core.macro_tracker import MACRO_TICKERS

    # Flatten all macro tickers
    macro_tickers = set()
    for _category, items in MACRO_TICKERS.items():
        macro_tickers.update(items.keys())

    # Union of benchmark options and macro indicators
    all_sync_tickers = sorted(list(set(BENCHMARK_TICKERS).union(macro_tickers)))

    logger.info(
        f"Fetching {BENCHMARK_HISTORY_DAYS}-day history for {len(all_sync_tickers)} sync tickers (benchmarks + macro)..."
    )

    success_count = 0
    for ticker in all_sync_tickers:
        try:
            history = await mdm.get_history(ticker, days=BENCHMARK_HISTORY_DAYS, force_refresh=True)
            if history and len(history) >= 30:
                logger.info(f"Stored {len(history)} price points for ticker {ticker}")
                success_count += 1

                # Calculate returns and 30-day volatility metrics
                history_30 = history[:30]
                returns = []
                for i in range(len(history_30) - 1):
                    prev = float(history_30[i + 1]["price"])
                    curr = float(history_30[i]["price"])
                    if prev > 0:
                        returns.append((curr - prev) / prev)

                today_px = float(history[0]["price"])
                yesterday_close = float(history[1]["price"]) if len(history) > 1 else today_px
                today_pct_change = (today_px - yesterday_close) / yesterday_close * 100 if yesterday_close > 0 else 0.0

                stdev_pct = 0.0
                regime_flag = "Normal"
                if len(returns) > 2:
                    mean_return = sum(returns) / len(returns)
                    variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
                    stdev_pct = math.sqrt(variance) * 100

                    # Match exact logic for high/unusual/normal regime flags
                    if abs(today_pct_change) > (2.0 * stdev_pct):
                        regime_flag = "⚠️ HIGHLY UNUSUAL"
                    elif abs(today_pct_change) > (1.5 * stdev_pct):
                        regime_flag = "❗ UNUSUAL"

                # Keep existing market_cap if present in database cache
                try:
                    res_mcap = mdm.client.table("market_data_cache").select("market_cap").eq("ticker", ticker).execute()
                    market_cap = res_mcap.data[0]["market_cap"] if res_mcap.data else 0
                except Exception:
                    market_cap = 0

                # Upsert pre-calculated metrics to market_data_cache
                cache_payload = {
                    "ticker": ticker,
                    "price": today_px,
                    "market_cap": market_cap,
                    "fetched_at": history[0]["fetched_at"],
                    "today_pct_change": today_pct_change,
                    "stdev_pct": stdev_pct,
                    "regime_flag": regime_flag,
                }
                mdm.client.table("market_data_cache").upsert(cache_payload).execute()
                logger.info(
                    f"Pre-calculated metrics saved for {ticker}: {today_pct_change:+.2f}%, {stdev_pct:.2f}% stdev, {regime_flag}"
                )
            else:
                logger.warning(f"Insufficient data for ticker {ticker}: {len(history) if history else 0} points")
        except Exception as e:
            logger.error(f"Failed to fetch ticker {ticker}: {e}")

    logger.info(
        f"Ticker history update complete. Updated {success_count}/{len(all_sync_tickers)} tickers and saved pre-calculated stats."
    )


if __name__ == "__main__":
    asyncio.run(update_prices())
