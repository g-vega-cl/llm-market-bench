"""Verification script for Portfolio Snapshot Upsert."""

import asyncio
import logging
from execution.portfolio import Portfolio
from execution.market_data import MarketDataManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify")

async def verify_portfolio_upsert():
    """Verify that portfolio snapshots can be upserted without conflict."""
    
    owner_id = "test_agent_upsert"
    portfolio = Portfolio(owner_id=owner_id)
    await portfolio.initialize()
    
    # We need a dummy price map
    price_map = {"AAPL": 150.0, "MSFT": 300.0}
    
    print(f"\n1. Recording first snapshot for {owner_id}...")
    await portfolio.record_performance_snapshot(price_map)
    print("✅ First snapshot recorded.")
    
    print(f"\n2. Recording second snapshot (upsert) for {owner_id}...")
    # This should now succeed instead of raising 409
    await portfolio.record_performance_snapshot(price_map)
    print("✅ Second snapshot (upsert) recorded successfully.")

if __name__ == "__main__":
    asyncio.run(verify_portfolio_upsert())
