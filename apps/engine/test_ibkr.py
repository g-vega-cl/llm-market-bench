import asyncio
import os
import sys
import logging
import random
from math import isnan
from dotenv import load_dotenv

# Add current directory to path (apps/engine)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv(".env")

from ib_async import IB, Stock, util
from execution.providers.ibkr import IBKRProvider
from core.config import IBKR_HOST, IBKR_PORT, logger

async def test_ibkr():
    """
    Robust IBKR connection test script.
    Checks for price and market cap data, specifically handling delayed/frozen data.
    """
    print("Starting Robust IBKR Provider Test...")
    
    ib = IB()
    client_id = random.randint(1000, 9999)
    print(f"Connecting to IBKR at {IBKR_HOST}:{IBKR_PORT} with clientId={client_id}...")
    
    try:
        await ib.connectAsync(IBKR_HOST, IBKR_PORT, clientId=client_id, readonly=True)
        print("Connected!")
        
        # Try Delayed Frozen (Type 4) which is often better when markets are closed
        print("Setting Market Data Type to 4 (Delayed Frozen)...")
        ib.reqMarketDataType(4)
        
        # Test a mix of tickers: ones the user owns and the problematic ones
        tickers = ["WMT", "META", "AAPL", "SPGI", "MCD"]
        
        for ticker in tickers:
            print(f"\n--- Testing {ticker} ---")
            contract = Stock(ticker, "SMART", "USD")
            qualified = await ib.qualifyContractsAsync(contract)
            if not qualified:
                print(f"FAILED to qualify {ticker}")
                continue
            
            contract = qualified[0]
            print(f"Qualified Contract: {contract.symbol} (ConId: {contract.conId})")
            
            # Request Ticker (Non-snapshot first to allow stream to start)
            t = ib.reqMktData(contract, "", False, False)
            
            print("Waiting 5 seconds for data to populate...")
            await asyncio.sleep(5)
            
            print(f"Ticker properties for {ticker}:")
            print(f"  marketPrice(): {t.marketPrice()}")
            print(f"  last: {t.last}")
            print(f"  close: {t.close}")
            print(f"  bid: {t.bid}")
            print(f"  ask: {t.ask}")
            
            price = t.marketPrice()
            if price is None or (isinstance(price, float) and isnan(price)) or price <= 0:
                 price = t.last
            if price is None or (isinstance(price, float) and isnan(price)) or price <= 0:
                 price = t.close
            if price is None or (isinstance(price, float) and isnan(price)) or price <= 0:
                 price = t.bid
            if price is None or (isinstance(price, float) and isnan(price)) or price <= 0:
                 price = t.ask
            
            if price is None or (isinstance(price, float) and isnan(price)) or price <= 0:
                print(f"!!! Still no valid price for {ticker} !!!")
            else:
                print(f"SUCCESS: Found price {price} for {ticker}")
                
            # Cancel subscription to be clean
            ib.cancelMktData(contract)
                
    except Exception as e:
        print(f"Connection/Test failed: {e}")
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("Disconnected.")

if __name__ == "__main__":
    asyncio.run(test_ibkr())
