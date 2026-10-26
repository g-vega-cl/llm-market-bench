import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.db import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_state")


async def reset_database(llm_only: bool = True):
    """Resets portfolio state, positions, trades, and performance.

    Args:
        llm_only: If True, only resets non-system LLM portfolios (owner_id not starting with 'sys-').
                  If False, resets all portfolios including mechanical benchmark strategies.
    """
    supabase = get_supabase_client()

    # 1. Fetch portfolios to determine target set
    res = supabase.table("portfolios").select("id, owner_id").execute()
    all_portfolios = res.data or []

    if llm_only:
        targets = [p for p in all_portfolios if not str(p.get("owner_id", "")).startswith("sys-")]
        logger.info(f"Targeting {len(targets)} LLM portfolios for reset (preserving system portfolios).")
    else:
        targets = all_portfolios
        logger.info(f"Targeting ALL {len(targets)} portfolios for reset.")

    if not targets:
        logger.info("No target portfolios found to reset.")
        return

    target_ids = [p["id"] for p in targets]
    target_owners = [p["owner_id"] for p in targets]

    # 2. Reset decisions
    if llm_only:
        logger.info(f"Resetting decisions for {len(target_owners)} LLM models...")
        for owner in target_owners:
            supabase.table("decisions").delete().eq("model_name", owner).execute()
    else:
        logger.info("Resetting all decisions...")
        supabase.table("decisions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    # 3. Reset trades
    logger.info(f"Resetting trades for {len(target_ids)} portfolios...")
    for pid in target_ids:
        supabase.table("trades").delete().eq("portfolio_id", pid).execute()

    # 4. Reset portfolio_positions
    logger.info(f"Resetting positions for {len(target_ids)} portfolios...")
    for pid in target_ids:
        supabase.table("portfolio_positions").delete().eq("portfolio_id", pid).execute()

    # 5. Reset portfolio_performance
    logger.info(f"Resetting performance snapshots for {len(target_ids)} portfolios...")
    for pid in target_ids:
        supabase.table("portfolio_performance").delete().eq("portfolio_id", pid).execute()

    # 6. Reset portfolio metrics to Cash-Only default state ($10,000 cash, BP = cash)
    logger.info("Resetting portfolio balances to $10,000 (Cash-Only Buying Power = $10,000)...")
    for p in targets:
        supabase.table("portfolios").update(
            {
                "cash_balance": 10000.00,
                "total_equity": 10000.00,
                "buying_power": 10000.00,
                "excess_liquidity": 10000.00,
                "maintenance_margin": 0.0,
                "sma": 10000.00,
                "realized": 10000.00,
                "last_updated_at": "now()",
            }
        ).eq("id", p["id"]).execute()
        logger.info(f"Reset portfolio for {p['owner_id']}")

    logger.info("Portfolio reset complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset portfolio state and historical trades.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Reset ALL portfolios including mechanical benchmark strategies (default is LLM-only).",
    )
    args = parser.parse_args()

    asyncio.run(reset_database(llm_only=not args.all))
