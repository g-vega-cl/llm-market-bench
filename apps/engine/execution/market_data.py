"""Market data manager with persistent caching.

This module provides the MarketDataManager class, which coordinates between
external financial APIs and a local database cache to optimize data retrieval.
"""

import datetime
from typing import Optional

from core.config import logger
from core.db import get_supabase_client
from .providers.base import FinancialProvider, TickerData
from .providers.factory import get_financial_provider

class MarketDataManager:
    """Manages market data retrieval with a database-backed cache."""

    def __init__(self, cache_ttl_hours: int = 4):
        self.client = get_supabase_client()
        self.provider: FinancialProvider = get_financial_provider()
        self.cache_ttl_hours = cache_ttl_hours

    async def get_quote(self, ticker: str, force_refresh: bool = False) -> Optional[TickerData]:
        """Fetch stock quote, checking cache first unless force_refresh is True.
        
        Args:
            ticker: The stock ticker symbol.
            force_refresh: Whether to bypass the cache and fetch fresh data.
            
        Returns:
            TickerData if found, None otherwise.
        """
        if not ticker or not isinstance(ticker, str):
            return None
            
        ticker = ticker.upper()
        
        # 1. Check Cache (unless force_refresh is True)
        if not force_refresh:
            cached_data = self._get_from_cache(ticker)
            if cached_data:
                return cached_data

        # 2. Fetch from Provider with Exponential Backoff
        logger.info(f"Cache miss for {ticker}. Fetching from provider...")
        import asyncio
        for attempt in range(1, 4):
            try:
                data = await self.provider.get_ticker_data(ticker)
                
                if data and data.exists:
                    # Key fix: if price is NaN, treat as missing and proceed to fallback/retry
                    import math
                    if math.isnan(data.price):
                        logger.warning(f"Provider returned NaN price for {ticker}. Proceeding...")
                        continue

                    # 3. Save to Cache and Return
                    self._save_to_cache(data)
                    return data
            except Exception as e:
                logger.warning(f"Attempt {attempt}/3 failed for {ticker}: {e}")
            
            # If we failed or got no data, wait before retrying (unless it's the last attempt)
            if attempt < 3:
                wait_time = 2 ** (attempt - 1)  # 1s, 2s, 4s...
                logger.info(f"Retrying {ticker} in {wait_time}s...")
                await asyncio.sleep(wait_time)

        # 4. Fallback: Last Known Price from History
        logger.warning(f"All retrieval attempts failed for {ticker}. Checking price history for fallback...")
        last_known = self._get_last_known_price(ticker)
        if last_known:
             logger.info(f"Using last known price for {ticker}: ${last_known.price}")
             return last_known

        return None

    def _get_last_known_price(self, ticker: str) -> Optional[TickerData]:
        """Retrieves the most recent price from the history table."""
        try:
             # We want the latest entry from price_history
             response = self.client.table("price_history") \
                .select("*") \
                .eq("ticker", ticker) \
                .order("fetched_at", desc=True) \
                .limit(1) \
                .execute()
             
             if response.data:
                 record = response.data[0]
                 return TickerData(
                     ticker=record["ticker"],
                     price=float(record["price"]),
                     market_cap=float(record["market_cap"]),
                     exists=True
                 )
        except Exception as e:
             logger.error(f"Error fetching last known price for {ticker}: {e}")
        
        return None

    def _get_from_cache(self, ticker: str) -> Optional[TickerData]:
        """Internal helper to retrieve and validate cached data."""
        try:
            response = self.client.table("market_data_cache") \
                .select("*") \
                .eq("ticker", ticker) \
                .execute()
            
            if not response.data:
                return None
            
            record = response.data[0]
            fetched_at = datetime.datetime.fromisoformat(record["fetched_at"].replace("Z", "+00:00"))
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # Check if cache is stale
            if (now - fetched_at).total_seconds() > (self.cache_ttl_hours * 3600):
                logger.debug(f"Cache entry for {ticker} is stale.")
                return None
            
            return TickerData(
                ticker=record["ticker"],
                price=float(record["price"]),
                market_cap=float(record["market_cap"]),
                exists=True
            )
        except Exception as e:
            logger.error(f"Error reading market data cache for {ticker}: {e}")
            return None

    def _save_to_cache(self, data: TickerData):
        """Internal helper to upsert data into the cache and record price history."""
        try:
            import math
            # Skip saving if data is NaN
            if math.isnan(data.price) or math.isnan(data.market_cap):
                logger.warning(f"Skipping cache save for {data.ticker} due to NaN values: price={data.price}, market_cap={data.market_cap}")
                return

            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            payload = {
                "ticker": data.ticker,
                "price": data.price,
                "market_cap": data.market_cap,
                "fetched_at": now_iso
            }

            # Upsert into the cache for fast lookups of the latest price
            self.client.table("market_data_cache").upsert(payload).execute()

            # Insert into history table for a permanent record
            self.client.table("price_history").insert(payload).execute()

        except Exception as e:
            logger.error(f"Error saving market data for {data.ticker}: {e}")

    async def get_history(self, ticker: str, days: int = 14) -> list[dict]:
        """Fetch historical price data, checking local DB first.
        
        Args:
            ticker: The stock ticker symbol.
            days: Number of days of history to retrieve.
            
        Returns:
            List of dicts with 'price' and 'fetched_at'.
        """
        ticker = ticker.upper()
        
        # 1. Check local DB
        try:
            res = self.client.table("price_history") \
                .select("price, fetched_at") \
                .eq("ticker", ticker) \
                .order("fetched_at", desc=True) \
                .limit(days) \
                .execute()
            
            # If we have enough data (at least 70% of requested days)
            if res.data and len(res.data) >= (days * 0.7):
                logger.debug(f"Using local price history for {ticker} ({len(res.data)} samples).")
                return [{
                    "price": float(row["price"]),
                    "fetched_at": row["fetched_at"]
                } for row in res.data]
        except Exception as e:
            logger.warning(f"Error checking local price history for {ticker}: {e}")

        # 2. Fetch from Provider
        logger.info(f"Local history insufficient for {ticker}. Fetching from provider...")
        history = await self.provider.get_history(ticker, days)
        
        if history:
            return history
            
        return []
