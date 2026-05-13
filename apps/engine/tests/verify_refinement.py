import asyncio
import os
import sys

# Add current directory to sys.path
sys.path.append(os.getcwd())

from execution.providers.ibkr import IBKRProvider


async def verify_refinement():
    print("Verifying IBKR refinement (readonly=True, suppressed logs)...")
    provider = IBKRProvider()
    ticker = "AAPL"
    
    # We expect NO 'INFO: position:' logs from ib_async here
    data = await provider.get_ticker_data(ticker)
    
    if data:
        print(f"SUCCESS: Fetched data for {ticker}")
        print(f"Price: {data.price}")
        print(f"Market Cap: {data.market_cap / 1e9:.2f}B")
    else:
        print(f"FAILURE: Could not fetch data for {ticker}")

if __name__ == "__main__":
    asyncio.run(verify_refinement())
