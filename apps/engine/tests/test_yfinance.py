import asyncio
import os
import sys

import pytest

# Add apps/engine to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.providers.yfinance import YFinanceProvider


@pytest.mark.asyncio
async def test_yfinance():
    print("Starting yfinance Verification Test...")

    provider = YFinanceProvider()
    tickers = ["AAPL", "TSLA", "MSFT"]

    for ticker in tickers:
        print(f"\nFetching data for {ticker}...")
        try:
            data = await provider.get_ticker_data(ticker)
            if data:
                print(f"SUCCESS: {ticker}")
                print(f"  Price: ${data.price}")
                print(f"  Market Cap: ${data.market_cap / 1e9:.2f}B")
                print(f"  Currency: {data.currency}")
                print(f"  Exchange: {data.exchange}")
            else:
                print(f"FAILED: {ticker} (No data returned)")

            print(f"Fetching history for {ticker} (5 days)...")
            history = await provider.get_history(ticker, days=5)
            if history:
                print(f"SUCCESS: {len(history)} bars retrieved.")
                for bar in history:
                    print(f"  {bar['fetched_at']}: ${bar['price']}")
            else:
                print(f"FAILED: {ticker} (No history returned)")

        except Exception as e:
            print(f"ERROR: {ticker} - {str(e)}")

    print("\nTest complete.")


if __name__ == "__main__":
    asyncio.run(test_yfinance())
