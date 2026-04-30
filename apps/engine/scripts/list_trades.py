import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from core.db import get_supabase_client

async def list_all_portfolios():
    supabase = get_supabase_client()
    print("--- All Portfolios ---")
    res = supabase.table("portfolios").select("*").execute()
    
    if res.data:
        for p in res.data:
            print(f"ID: {p['id']} | Owner: {p['owner_id']} | Cash: {p['cash_balance']} | Equity: {p['total_equity']} | SMA: {p['sma']}")
            
            # Get trades for this portfolio
            t_res = supabase.table("trades").select("*").eq("portfolio_id", p['id']).order("executed_at", desc=True).execute()
            if t_res.data:
                print(f"  Recent Trades:")
                for t in t_res.data[:3]:
                    print(f"    {t['executed_at']} | {t['signal']} {t['quantity']} {t['ticker']} @ {t['price']}")
            else:
                print("  No trades found.")
            print("-" * 20)
    else:
        print("No portfolios found.")

if __name__ == "__main__":
    asyncio.run(list_all_portfolios())
