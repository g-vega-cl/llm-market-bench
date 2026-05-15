import asyncio
import logging
import math
import os
from typing import List, Optional
from xml.etree import ElementTree as ET

from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ib_async import IB, Stock, util
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("ibkr-proxy")

# --- Config ---
IBKR_PROXY_API_KEY = os.getenv("IBKR_PROXY_API_KEY")
IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
IBKR_PORT = int(os.getenv("IBKR_PORT", "7496"))
IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "10"))

# --- Models ---
class TickerData(BaseModel):
    ticker: str
    price: float
    market_cap: float
    exists: bool
    currency: str
    exchange: str

class HistoryItem(BaseModel):
    price: float
    fetched_at: str

# --- Auth ---
security = HTTPBearer()

async def get_current_user(token: HTTPAuthorizationCredentials = Security(security)):
    if not IBKR_PROXY_API_KEY:
        logger.error("IBKR_PROXY_API_KEY not set")
        raise HTTPException(status_code=500, detail="Server configuration error")
    
    if token.credentials != IBKR_PROXY_API_KEY:
        logger.warning("Invalid API Key provided")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    return {"user": "admin"}

# --- IBKR Client ---
class IBKRManager:
    _ib: Optional[IB] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_client(cls) -> IB:
        import random
        async with cls._lock:
            if cls._ib is not None and cls._ib.isConnected():
                return cls._ib

            util.patchAsyncio()
            
            # Try connecting with a few different Client IDs if the first one fails
            max_attempts = 3
            last_err = None
            
            for attempt in range(max_attempts):
                client_id = random.randint(1001, 9999) if attempt > 0 or not IBKR_CLIENT_ID else IBKR_CLIENT_ID
                cls._ib = IB()
                logger.info(f"Connecting to IBKR at {IBKR_HOST}:{IBKR_PORT} (Attempt {attempt+1}/{max_attempts}, ClientId: {client_id})...")
                
                try:
                    await asyncio.wait_for(
                        cls._ib.connectAsync(IBKR_HOST, IBKR_PORT, clientId=client_id, readonly=True),
                        timeout=15
                    )
                    logger.info(f"Successfully connected to IBKR with ClientId {client_id}.")
                    cls._ib.reqMarketDataType(3)  # Delayed
                    cls._ib.reqMarketDataType(4)  # Delayed Frozen
                    return cls._ib
                except Exception as e:
                    last_err = e
                    logger.warning(f"Connection attempt {attempt+1} failed: {e}")
                    if cls._ib and cls._ib.isConnected():
                        cls._ib.disconnect()
                    await asyncio.sleep(1) # Short delay before retry
            
            logger.error(f"All {max_attempts} connection attempts to IBKR failed.")
            raise HTTPException(status_code=503, detail=f"IBKR Connection failed: {str(last_err)}")

manager = IBKRManager()

app = FastAPI(title="IBKR Proxy API")

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "IBKR Proxy is running"}

@app.get("/price/{ticker}", response_model=TickerData)
async def get_price(ticker: str, user=Depends(get_current_user)):
    ib = await manager.get_client()
    try:
        contract = Stock(ticker, "SMART", "USD")
        qualified = await ib.qualifyContractsAsync(contract)
        if not qualified:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
        
        contract = qualified[0]
        tickers = await ib.reqTickersAsync(contract)
        if not tickers:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")
        
        t = tickers[0]
        price = t.marketPrice()
        if price is None or math.isnan(price) or price <= 0:
            price = t.last or t.close or t.bid or t.ask
        
        if price is None or math.isnan(price) or price <= 0:
            raise HTTPException(status_code=404, detail=f"Could not find valid price for {ticker}")

        # Market Cap
        market_cap = 0.0
        try:
            fundamental_xml = await ib.reqFundamentalDataAsync(contract, "ReportSnapshot")
            if fundamental_xml:
                root = ET.fromstring(fundamental_xml)
                for ratio in root.findall(".//Ratio"):
                    if ratio.get("FieldName") == "MKTCAP":
                        market_cap = float(ratio.text) * 1e6
                        break
        except Exception as e:
            logger.warning(f"Error fetching fundamentals for {ticker}: {e}")

        return TickerData(
            ticker=ticker,
            price=float(price),
            market_cap=float(market_cap),
            exists=True,
            currency="USD",
            exchange=contract.exchange
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error fetching {ticker}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/history/{ticker}", response_model=List[HistoryItem])
async def get_history(ticker: str, days: int = 14, user=Depends(get_current_user)):
    ib = await manager.get_client()
    try:
        contract = Stock(ticker, "SMART", "USD")
        qualified = await ib.qualifyContractsAsync(contract)
        if not qualified:
            return []
        
        contract = qualified[0]
        duration = f"{days} D"
        bars = await ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True
        )
        
        if not bars:
            return []
        
        return [
            {
                "price": float(bar.close),
                "fetched_at": bar.date.isoformat() if hasattr(bar.date, "isoformat") else str(bar.date)
            }
            for bar in reversed(bars)
        ]
    except Exception:
        logger.exception(f"Error fetching history for {ticker}")
        raise HTTPException(status_code=500, detail="Internal server error")
