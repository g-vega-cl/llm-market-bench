import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio

from core.db import get_supabase_client


async def check_failed_decisions():
    supabase = get_supabase_client()
    model_name = "gpt-5.4-nano"
    
    print(f"--- Decisions for {model_name} ---")
    res = supabase.table("decisions").select("*").eq("model_name", model_name).execute()
    
    if res.data:
        for d in res.data:
            metadata = d.get("metadata", {})
            info = metadata.get("info", "")
            # Look for quantity in metadata or decision object
            qty = metadata.get("quantity") or getattr(d, "quantity", "N/A")
            price = metadata.get("price") or d.get("price", "N/A")
            print(f"{d['status']} | {d['signal']} {qty} {d['ticker']} @ {price} | {info}")
    else:
        print("No decisions found.")
    
if __name__ == "__main__":
    asyncio.run(check_failed_decisions())
