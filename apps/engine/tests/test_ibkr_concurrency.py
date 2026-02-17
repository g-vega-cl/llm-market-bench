import asyncio
import os
import sys
import logging

# Add apps/engine to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.providers.ibkr import IBKRProvider
from core.config import logger

import pytest

@pytest.mark.asyncio
async def test_concurrency():
    print("Starting IBKR Multi-Instance Concurrency Test...")
    
    tickers = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
    
    # We create a NEW provider instance for each ticker, which was the source of the bug
    print(f"Fetching data for {len(tickers)} tickers simultaneously using separate provider instances...")
    
    async def fetch(ticker):
        provider = IBKRProvider()
        return await provider.get_ticker_data(ticker)

    tasks = [fetch(ticker) for ticker in tickers]
    
    results = await asyncio.gather(*tasks)
    
    success_count = 0
    for i, res in enumerate(results):
        if res:
            print(f"SUCCESS: {tickers[i]} - Price: ${res.price}")
            success_count += 1
        else:
            print(f"FAILED: {tickers[i]}")
            
    print(f"\nSummary: {success_count}/{len(tickers)} succeeded.")
    
    # Cleanup
    await IBKRProvider.disconnect_all()
    print("Test complete.")

if __name__ == "__main__":
    # Ensure we have .env loaded if needed, but IBKRProvider handles its own config
    asyncio.run(test_concurrency())
