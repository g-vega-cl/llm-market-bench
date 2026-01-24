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

    async def get_quote(self, ticker: str) -> Optional[TickerData]:
        """Fetch stock quote, checking cache first.
        
        Args:
            ticker: The stock ticker symbol.
            
        Returns:
            TickerData if found, None otherwise.
        """
        ticker = ticker.upper()
        
        # 1. Check Cache
        cached_data = self._get_from_cache(ticker)
        if cached_data:
            return cached_data

        # 2. Fetch from Provider
        logger.info(f"Cache miss for {ticker}. Fetching from provider...")
        data = await self.provider.get_ticker_data(ticker)
        
        if data and data.exists:
            # 3. Save to Cache
            self._save_to_cache(data)
            return data
            
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
