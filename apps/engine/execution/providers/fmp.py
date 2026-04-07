"""Financial Modeling Prep (FMP) implementation of FinancialProvider."""

import asyncio
import time
import httpx
from typing import Optional
from .base import FinancialProvider, TickerData
from core.config import FMP_API_KEY, logger


class FMPProvider(FinancialProvider):
    """Provider for Financial Modeling Prep API."""

    BASE_URL = "https://financialmodelingprep.com/stable"
    _last_call_time = 0.0  # Shared across all instances to throttle globally

    def __init__(self):
        if not FMP_API_KEY:
            logger.warning("FMP_API_KEY not found in environment. FMP validation will be disabled.")
        self.api_key = FMP_API_KEY

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

    async def get_ticker_data_batch(self, tickers: list[str]) -> dict[str, TickerData]:
        """Fetch real-time/delayed ticker data for multiple symbols.
        
        Since stable/batch-quote is restricted on some plans (402), 
        we use parallel individual calls for guaranteed compatibility 
        while maintaining high performance.
        """
        if not self.api_key or not tickers:
            return {}

        results = {}
        # Concurrency limit to avoid being flagged for burst/DOS
        semaphore = asyncio.Semaphore(10)

        async def fetch_one(ticker):
            async with semaphore:
                # We reuse the existing get_ticker_data which already has throttling
                return ticker, await self.get_ticker_data(ticker)

        # Gather all tasks
        tasks = [fetch_one(t) for t in tickers]
        batch_results = await asyncio.gather(*tasks)

        for ticker, data in batch_results:
            if data:
                results[ticker] = data
        
        return results

    async def get_history(self, ticker: str, days: int = 14) -> list[dict]:
        """Fetch historical price data using FMP."""
        if not self.api_key:
            return []

        try:
            async with httpx.AsyncClient() as client:
                # FMP historical-price-eod/full requires symbol as query parameter
                resp = await client.get(
                    f"{self.BASE_URL}/historical-price-eod/full",
                    params={"symbol": ticker, "timeseries": days, "apikey": self.api_key}
                )
                resp.raise_for_status()
                data = resp.json()

                # Handle both list (stable/v4) and dict with 'historical' key (v3)
                historical_data = data if isinstance(data, list) else data.get("historical", [])

                if not historical_data:
                    logger.warning(f"No history found for {ticker} on FMP.")
                    return []

                results = []
                for entry in historical_data:
                    results.append({
                        "price": float(entry["close"]),
                        "fetched_at": entry["date"] # FMP provides YYYY-MM-DD
                    })
                
                # FMP usually returns descending (latest first)
                return results

        except Exception as e:
            logger.error(f"Error fetching history from FMP for {ticker}: {e}")
            return []

    async def search_tickers(self, query: str, limit: int = 5) -> list[dict]:
        """Search for tickers by name or symbol using FMP."""
        if not self.api_key:
            return []

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/search-symbol",
                    params={"query": query, "limit": limit, "apikey": self.api_key}
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Error searching tickers on FMP for '{query}': {e}")
            return []

    async def screen_stocks(
        self, 
        market_cap_more_than: Optional[float] = None, 
        market_cap_lower_than: Optional[float] = None,
        price_more_than: Optional[float] = None,
        price_lower_than: Optional[float] = None,
        beta_more_than: Optional[float] = None,
        beta_lower_than: Optional[float] = None,
        volume_more_than: Optional[float] = None,
        volume_lower_than: Optional[float] = None,
        dividend_more_than: Optional[float] = None,
        dividend_lower_than: Optional[float] = None,
        sector: Optional[str] = None, 
        industry: Optional[str] = None, 
        exchange: Optional[str] = "NYSE,NASDAQ",
        limit: int = 10,
        is_actively_trading: bool = True
    ) -> list[dict]:
        """Screen stocks using FMP /company-screener with advanced filters."""
        if not self.api_key:
            return []

        # Construction of parameters for FMP API
        # Mapping our snake_case snake_case to FMP's camelCase
        params = {
            "limit": min(limit, 15), # Cap at 15 for context efficiency
            "apikey": self.api_key,
            "isActivelyTrading": str(is_actively_trading).lower()
        }

        if exchange:
            params["exchange"] = exchange
        if sector:
            params["sector"] = sector
        if industry:
            params["industry"] = industry
        
        # Numeric filters
        if market_cap_more_than is not None:
            params["marketCapMoreThan"] = market_cap_more_than
        elif not sector and not industry:
            # Default to 1B+ if no specific sector/industry to ensure baseline liquidity
            params["marketCapMoreThan"] = 1000000000
            
        if market_cap_lower_than is not None:
            params["marketCapLowerThan"] = market_cap_lower_than
        if price_more_than is not None:
            params["priceMoreThan"] = price_more_than
        if price_lower_than is not None:
            params["priceLowerThan"] = price_lower_than
        if beta_more_than is not None:
            params["betaMoreThan"] = beta_more_than
        if beta_lower_than is not None:
            params["betaLowerThan"] = beta_lower_than
        if volume_more_than is not None:
            params["volumeMoreThan"] = volume_more_than
        if volume_lower_than is not None:
            params["volumeLowerThan"] = volume_lower_than
        if dividend_more_than is not None:
            params["dividendMoreThan"] = dividend_more_than
        if dividend_lower_than is not None:
            params["dividendLowerThan"] = dividend_lower_than

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/company-screener",
                    params=params
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Error screening stocks on FMP: {e}")
            return []
