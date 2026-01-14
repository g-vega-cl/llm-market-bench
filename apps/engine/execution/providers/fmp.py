"""Financial Modeling Prep (FMP) implementation of FinancialProvider."""

import asyncio
import time
import httpx
from typing import Optional
from .base import FinancialProvider, TickerData
from core.config import FINANCIAL_API_KEY, logger


class FMPProvider(FinancialProvider):
    """Provider for Financial Modeling Prep API."""

    BASE_URL = "https://financialmodelingprep.com/stable"
    _last_call_time = 0.0  # Shared across all instances to throttle globally

    def __init__(self):
        if not FINANCIAL_API_KEY:
            logger.warning("FINANCIAL_API_KEY not found in environment. FMP validation will be disabled.")
        self.api_key = FINANCIAL_API_KEY

    async def get_ticker_data(self, ticker: str) -> Optional[TickerData]:
        if not self.api_key:
            return None

        # Throttling logic
        from core.config import FINANCIAL_API_THROTTLE_SECONDS
        if FINANCIAL_API_THROTTLE_SECONDS > 0:
            elapsed = time.time() - FMPProvider._last_call_time
            wait_time = FINANCIAL_API_THROTTLE_SECONDS - elapsed
            if wait_time > 0:
                logger.debug(f"Throttling FMP call for {ticker}: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        # Update last call time just before the request
        FMPProvider._last_call_time = time.time()

        try:
            async with httpx.AsyncClient() as client:
                # 1. Get Consolidated Quote (Price + Market Cap)
                quote_resp = await client.get(
                    f"{self.BASE_URL}/quote",
                    params={"symbol": ticker, "apikey": self.api_key}
                )
                quote_resp.raise_for_status()
                quote_data = quote_resp.json()

                if not quote_data:
                    logger.warning(f"Ticker {ticker} not found on FMP.")
                    return None

                q = quote_data[0]

                return TickerData(
                    ticker=ticker,
                    price=float(q.get("price", 0)),
                    market_cap=float(q.get("marketCap", 0)),
                    exists=True,
                    currency=q.get("currency", "USD"),
                    exchange=q.get("exchange")
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 402:
                logger.error(f"FMP API Quota Exceeded (402 Payment Required): {e.response.url}")
            else:
                logger.error(f"HTTP error fetching data from FMP for {ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching data from FMP for {ticker}: {e}")
            return None
