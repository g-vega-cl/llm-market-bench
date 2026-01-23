"""Script to update market prices and recalculate portfolio metrics without LLM calls."""

import asyncio
from core.config import logger
from core.db import get_supabase_client
from execution.market_data import MarketDataManager
from execution.portfolio import Portfolio

async def update_prices():
    """Main function to update prices and metrics."""
    logger.info("Starting Price Update Script (No LLM)...")
    
    sb_client = get_supabase_client()
    mdm = MarketDataManager()
    
    # 1. Get all active portfolios
    try:
        port_res = sb_client.table("portfolios").select("owner_id").execute()
        owners = [p["owner_id"] for p in port_res.data] if port_res.data else []
    except Exception as e:
        logger.error(f"Failed to fetch portfolios: {e}")
        return

    if not owners:
        logger.warning("No portfolios found to update.")
        return

    logger.info(f"Found {len(owners)} portfolios to update.")

    # 2. Collect all unique tickers across all portfolios
    all_tickers = set()
    portfolios_to_update = []
    
    for owner in owners:
        p = Portfolio(owner_id=owner)
        await p.initialize()
        all_tickers.update(p.positions.keys())
        portfolios_to_update.append(p)
    
    logger.info(f"Identified {len(all_tickers)} unique tickers: {all_tickers}")

    # 3. Fetch fresh prices for all tickers
    price_map = {}
    for ticker in all_tickers:
        logger.info(f"Fetching fresh quote for {ticker}...")
        # get_quote handles caching if TTL hasn't expired, but for 
        # a dedicated 'update' script we might want to force refresh?
        # For now, let's keep the standard get_quote behavior.
        data = await mdm.get_quote(ticker)
        if data:
            price_map[ticker] = data.price
            logger.info(f"Updated price for {ticker}: ${data.price:.2f}")
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

if __name__ == "__main__":
    asyncio.run(update_prices())
