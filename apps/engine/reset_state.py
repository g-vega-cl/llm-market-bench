import asyncio
import logging
from core.db import get_supabase_client
from execution.reg_t_validation import RegTMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_state")

async def reset_database():
    supabase = get_supabase_client()
    
    logger.info("Resetting decisions...")
    supabase.table("decisions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    logger.info("Resetting trades...")
    supabase.table("trades").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    logger.info("Resetting portfolio_positions...")
    supabase.table("portfolio_positions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    logger.info("Resetting portfolio_performance...")
    supabase.table("portfolio_performance").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    
    # Optional: Reset newsletter snapshots if we want to force re-ingestion
    # logger.info("Resetting newsletter_snapshots...")
    # supabase.table("newsletter_snapshots").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    logger.info("Resetting portfolios to default state ($10,000)...")
    # Fetch all portfolios to reset them
    res = supabase.table("portfolios").select("id, owner_id").execute()
    if res.data:
        for p in res.data:
            # Default metrics for $10k cash and no positions
            equity = 10000.00
            buying_power = 40000.00
            excess_liquidity = 10000.00
            maintenance_margin = 0.0
            available_funds = 10000.00
            sma = 10000.00
            realized = 10000.00
            
            supabase.table("portfolios").update({
                "cash_balance": 10000.00,
                "total_equity": equity,
                "buying_power": buying_power,
                "excess_liquidity": excess_liquidity,
                "maintenance_margin": maintenance_margin,
                "sma": sma,
                "realized": realized,
                "last_updated_at": "now()"
            }).eq("id", p["id"]).execute()
            logger.info(f"Reset portfolio for {p['owner_id']}")
    else:
        logger.info("No portfolios found to reset.")

    logger.info("Database reset complete.")

if __name__ == "__main__":
    asyncio.run(reset_database())
