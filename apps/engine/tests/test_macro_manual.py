#!/usr/bin/env python3
"""Utility script to manually test the Global Macro Tracker.

This script can be run to verify the macro tracker is working correctly:
    python apps/engine/test_macro.py

Note: Requires FMP_API_KEY to be set in environment.
"""

import asyncio

from core.macro_tracker import MACRO_TICKERS
from execution.market_data import MarketDataManager


async def main():
    print("=" * 60)
    print("Global Macro Tracker Test Utility")
    print("=" * 60)
    
    print("\nConfigured Macro Tickers:")
    for category, tickers in MACRO_TICKERS.items():
        print(f"\n  [{category}]")
        for ticker, name in tickers.items():
            print(f"    {ticker}: {name}")
    
    print("\n" + "-" * 60)
    print("Testing Market Data Manager...")
    print("-" * 60)
    
    mdm = MarketDataManager()
    
    print("\nFetching quotes for all macro tickers...")
    all_tickers = []
    for category, items in MACRO_TICKERS.items():
        all_tickers.extend(items.keys())
    
    quotes = await mdm.get_quotes(all_tickers, force_refresh=True)
    
    print(f"\nSuccessfully fetched {len(quotes)} out of {len(all_tickers)} tickers:")
    for ticker in all_tickers:
        if ticker in quotes:
            q = quotes[ticker]
            print(f"  ✓ {ticker}: ${q.price:.2f}")
        else:
            print(f"  ✗ {ticker}: NOT FOUND")
    
    print("\n" + "-" * 60)
    print("Generating Global Macro Context...")
    print("-" * 60)
    
    from core.macro_tracker import get_global_macro_context
    context = await get_global_macro_context(mdm)
    
    print(context)
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
