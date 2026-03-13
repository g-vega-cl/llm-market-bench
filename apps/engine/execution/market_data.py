"""Market data manager with persistent caching.

This module provides the MarketDataManager class, which coordinates between
external financial APIs and a local database cache to optimize data retrieval.
"""

import datetime
import math
from typing import Optional

from core.config import logger
from core.db import get_supabase_client
from .providers.base import FinancialProvider, TickerData
from .providers.factory import get_financial_provider

class MarketDataManager:
    """Manages market data retrieval with a database-backed cache."""

    def __init__(self, cache_ttl_hours: int = 4):
        self.client = get_supabase_client()
        self.cache_ttl_hours = cache_ttl_hours
        
        # Initialize providers in priority order
        from core.config import FINANCIAL_PROVIDER, FALLBACK_FINANCIAL_PROVIDER, SECOND_FALLBACK_FINANCIAL_PROVIDER
        
        provider_names = [FINANCIAL_PROVIDER, FALLBACK_FINANCIAL_PROVIDER, SECOND_FALLBACK_FINANCIAL_PROVIDER]
        # Remove duplicates while preserving order
        seen = set()
        unique_provider_names = [x for x in provider_names if not (x in seen or seen.add(x))]
        
        self.providers = [get_financial_provider(name) for name in unique_provider_names]

    @property
    def provider(self):
        """Getter for the primary provider (first in the chain)."""
        return self.providers[0] if self.providers else None

    @provider.setter
    def provider(self, value):
        """Setter to allow manual override of the primary provider (for legacy tests)."""
        if self.providers:
            self.providers[0] = value
        else:
            self.providers = [value]

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

        # 2. Fetch from Providers in sequence
        data = None
        for i, provider in enumerate(self.providers):
            priority = "primary" if i == 0 else f"fallback {i}"
            logger.info(f"Fetching {ticker} from {priority} provider ({provider.provider_name})...")
            
            data = await self._fetch_with_backoff(provider, ticker)
            if data:
                break
            
            if i < len(self.providers) - 1:
                logger.warning(f"{priority.capitalize()} provider failed for {ticker}. Trying next fallback...")

        if data:
            # 3. Save to Cache and Return
            self._save_to_cache(data)
            return data

        # 4. Last Resort: Last Known Price from History
        last_known = self._get_last_known_price(ticker)
        if last_known:
             logger.info(f"All online retrieval failed for {ticker}. Using last known price: ${last_known.price}")
             return last_known

        logger.error(f"FATAL: All retrieval attempts failed for {ticker}. No historical data available.")
        return None

    async def _fetch_with_backoff(self, provider: FinancialProvider, ticker: str) -> Optional[TickerData]:
        """Helper to fetch data from a provider with retries and validation."""
        import asyncio
        from core.config import MARKET_DATA_RETRIES
        
        for attempt in range(1, MARKET_DATA_RETRIES + 1):
            try:
                data = await provider.get_ticker_data(ticker)
                
                if data and data.exists:
                    if math.isnan(data.price):
                        logger.warning(f"Provider {provider.provider_name} returned NaN price for {ticker}. Proceeding...")
                        continue
                    return data
            except Exception as e:
                # Reduce noise: don't log full stack trace for common timeouts/connection errors
                logger.debug(f"Attempt {attempt}/{MARKET_DATA_RETRIES} failed for {ticker} via {provider.provider_name}: {e}")
            
            if attempt < MARKET_DATA_RETRIES:
                wait_time = 2 ** (attempt - 1)
                await asyncio.sleep(wait_time)
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
                      market_cap=float(record["market_cap"]) if record.get("market_cap") else 0,
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
                market_cap=float(record["market_cap"]) if record.get("market_cap") else 0,
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

        # 2. Fetch from Providers in sequence
        history = None
        for i, provider in enumerate(self.providers):
            priority = "primary" if i == 0 else f"fallback {i}"
            logger.info(f"Fetching history for {ticker} from {priority} provider ({provider.provider_name})...")
            
            history = await provider.get_history(ticker, days)
            if history:
                break
            
            if i < len(self.providers) - 1:
                logger.warning(f"{priority.capitalize()} provider history failed for {ticker}. Trying next fallback...")
            
        if history:
            # 3. Save to history table so it's available next time
            try:
                for entry in history:
                    # Note: We don't have market_cap in history responses usually
                    # but we can insert what we have.
                    payload = {
                        "ticker": ticker,
                        "price": float(entry["price"]),
                        "fetched_at": entry["fetched_at"]
                    }
                    if "market_cap" in entry:
                        payload["market_cap"] = entry["market_cap"]
                    else:
                        payload["market_cap"] = 0 # Fallback for non-null column if migration not applied
                        
                    self.client.table("price_history").upsert(payload, on_conflict="ticker, fetched_at").execute()
            except Exception as e:
                logger.warning(f"Error saving historical data for {ticker} to cache: {e}")
            return history
            
        return []

