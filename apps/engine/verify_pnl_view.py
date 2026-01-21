import asyncio
import os
import sys
from uuid import uuid4

# Add path to load components
sys.path.append(os.path.join(os.getcwd(), "apps/engine"))

from core.db import get_supabase_client

async def verify_pnl():
    supabase = get_supabase_client()
    ticker = f"TEST_{uuid4().hex[:4]}"
    
    print(f"--- Verifying P&L View with {ticker} ---")
    
    # 1. Setup Test Data
    # Get a portfolio ID
    res = supabase.table("portfolios").select("id").limit(1).execute()
    if not res.data:
        print("Error: No portfolios found to test with.")
        return
    portfolio_id = res.data[0]["id"]
    
    try:
        # Create a dummy position
        # Cost Basis: 100, Qty: 10
        supabase.table("portfolio_positions").insert({
            "portfolio_id": portfolio_id,
            "ticker": ticker,
            "quantity": 10,
            "average_cost_basis": 100.00
        }).execute()
        
        # Create dummy market data
        # Price: 110 (10% gain, $100 P/L)
        supabase.table("market_data_cache").upsert({
            "ticker": ticker,
            "price": 110.00,
            "market_cap": 10000000000,
            "fetched_at": "now()"
        }).execute()
        
        # 2. Query the View
        view_res = supabase.table("position_pnl").select("*").eq("ticker", ticker).execute()
        
        if view_res.data:
            data = view_res.data[0]
            print(f"View Results for {ticker}:")
            print(f"  Qty: {data['quantity']}")
            print(f"  Cost: {data['average_cost_basis']}")
            print(f"  Price: {data['current_price']}")
            print(f"  P/L (USD): ${data['unrealized_pnl_usd']}")
            print(f"  P/L (%): {data['unrealized_pnl_pct']}%")
            
            # Assertions
            assert float(data['unrealized_pnl_usd']) == 100.00
            assert float(data['unrealized_pnl_pct']) == 10.0
            print("SUCCESS: Calculations are correct.")
        else:
            print("ERROR: Could not find test data in view.")
            
    finally:
        # 3. Cleanup
        supabase.table("portfolio_positions").delete().match({"ticker": ticker, "portfolio_id": portfolio_id}).execute()
        # market_data_cache might be shared, but we use a unique ticker
        supabase.table("market_data_cache").delete().eq("ticker", ticker).execute()
        print("--- Cleanup Complete ---")

if __name__ == "__main__":
    asyncio.run(verify_pnl())
