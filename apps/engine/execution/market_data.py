"""Market data manager with persistent caching.

This module provides the MarketDataManager class, which coordinates between
external financial APIs and a local database cache to optimize data retrieval.
"""

import datetime
import math
from typing import Optional

from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client
from .providers.base import FinancialProvider, TickerData
from .providers.factory import get_financial_provider

class MarketDataManager:
    """Manages market data retrieval with a database-backed cache."""

    _market_status_cache: dict = {
        "is_open": None,
        "fetched_at": None,
        "ttl_seconds": 300  # 5 minutes
    }

    # In-memory cache for screener results to avoid redundant API hits within a session
    _screener_cache: dict = {}

    def __init__(self, cache_ttl_seconds: Optional[int] = None):
        from core.config import FINANCIAL_PROVIDER, MARKET_DATA_CACHE_TTL_SECONDS
        self.client = get_supabase_client()
        self.cache_ttl_seconds = cache_ttl_seconds if cache_ttl_seconds is not None else MARKET_DATA_CACHE_TTL_SECONDS
        self.providers = [get_financial_provider(FINANCIAL_PROVIDER)]

    @property
    def provider(self):
        """Getter for the configured provider."""
        return self.providers[0] if self.providers else None

    @provider.setter
    def provider(self, value):
        """Setter to allow manual override of the configured provider."""
        if self.providers:
            self.providers[0] = value
        else:
            self.providers = [value]

    async def is_market_open(self) -> bool:
        """Checks if the US stock market (NASDAQ/NYSE) is currently open.

        Prioritizes FMP API for holiday awareness, falls back to time-based check.
        Uses a class-level cache to avoid repeated API calls within the same pipeline run.
        """
        import datetime
        
        # Check class-level cache first to avoid repeated API calls
        now = datetime.datetime.now(datetime.timezone.utc)
        cache = MarketDataManager._market_status_cache
        
        if cache["fetched_at"] is not None:
            elapsed = (now - cache["fetched_at"]).total_seconds()
            if elapsed < cache["ttl_seconds"]:
                logger.debug(f"Using cached market status: {'OPEN' if cache['is_open'] else 'CLOSED'}")
                return cache["is_open"]
        
        try:
            from zoneinfo import ZoneInfo
            now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
        except ImportError:
            # Fallback for environments without zoneinfo
            # Assuming server is in ET or just using UTC-5 as an approximation
            # But better to just use current local if zoneinfo fails
            now_et = datetime.datetime.now()
            logger.warning("zoneinfo not found, using local time for market hours baseline.")

        # 1. Primary Check: FMP API (Handles Holidays)
        if FMP_API_KEY:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    # Use NASDAQ as the proxy for US Market status
                    url = f"https://financialmodelingprep.com/stable/exchange-market-hours"
                    params = {"exchange": "NASDAQ", "apikey": FMP_API_KEY}
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()

                    if data and isinstance(data, list):
                        is_open = data[0].get("isMarketOpen", False)
                        logger.info(f"FMP Market Status (NASDAQ): {'OPEN' if is_open else 'CLOSED'}")
                        
                        # Cache the result
                        cache["is_open"] = is_open
                        cache["fetched_at"] = now
                        
                        return is_open
            except Exception as e:
                logger.warning(f"Failed to fetch market status from FMP: {e}. Falling back to time-based check.")

        # 2. Fallback Check: Time-based (Mon-Fri, 09:30-16:00 ET)
        # Weekends
        if now_et.weekday() >= 5: # 5=Sat, 6=Sun
            result = False
        else:
            market_start = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
            market_end = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
            result = market_start <= now_et <= market_end
        
        # Cache the fallback result as well
        cache["is_open"] = result
        cache["fetched_at"] = now
        
        return result

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

        # 2. Fetch from the configured provider
        provider = self.provider
        if provider is None:
            logger.error(f"No financial provider configured for {ticker}.")
            return None

        logger.info(f"Fetching {ticker} from configured provider ({provider.provider_name})...")
        data = await self._fetch_with_backoff(provider, ticker)

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
        """Exposes stock screening capabilities, checking cache first."""
        
        # Create a cache key from the parameters
        cache_key = f"{market_cap_more_than}-{market_cap_lower_than}-{price_more_than}-{price_lower_than}-{beta_more_than}-{beta_lower_than}-{volume_more_than}-{volume_lower_than}-{dividend_more_than}-{dividend_lower_than}-{sector}-{industry}-{exchange}-{limit}-{is_actively_trading}"
        
        if cache_key in MarketDataManager._screener_cache:
            logger.debug(f"Returning cached screener results for key: {cache_key[:30]}...")
            return MarketDataManager._screener_cache[cache_key]

        # Currently only FMP supports direct screening tool
        provider = self.provider # Primary provider
        if not hasattr(provider, "screen_stocks"):
            logger.error(f"Primary provider {provider.provider_name} does not support screening.")
            return []

        try:
            results = await provider.screen_stocks(
                market_cap_more_than=market_cap_more_than,
                market_cap_lower_than=market_cap_lower_than,
                price_more_than=price_more_than,
                price_lower_than=price_lower_than,
                beta_more_than=beta_more_than,
                beta_lower_than=beta_lower_than,
                volume_more_than=volume_more_than,
                volume_lower_than=volume_lower_than,
                dividend_more_than=dividend_more_than,
                dividend_lower_than=dividend_lower_than,
                sector=sector,
                industry=industry,
                exchange=exchange,
                limit=limit,
                is_actively_trading=is_actively_trading
            )
            
            # Save to cache
            MarketDataManager._screener_cache[cache_key] = results
            return results
            
        except Exception as e:
            logger.error(f"Error executing stock screen via {provider.provider_name}: {e}")
            return []

    async def get_quotes(self, tickers: list[str], force_refresh: bool = False) -> dict[str, TickerData]:
        """Fetch multiple stock quotes, checking cache first where possible.
        
        Args:
            tickers: List of stock ticker symbols.
            force_refresh: Whether to bypass the cache and fetch fresh data for all.
            
        Returns:
            Dict mapping ticker symbol to TickerData for all successfully retrieved stocks.
        """
        if not tickers:
            return {}

        tickers = [t.upper() for t in tickers]
        results = {}
        missing_tickers = list(tickers)

        # 1. Check Cache
        if not force_refresh:
            for ticker in tickers:
                cached = self._get_from_cache(ticker)
                if cached:
                    results[ticker] = cached
                    missing_tickers.remove(ticker)

        if not missing_tickers:
            return results

        # 2. Fetch missing from the configured provider
        provider = self.provider
        if provider is None:
            logger.error("No financial provider configured for batch quote retrieval.")
            return results

        logger.info(f"Batch fetching {len(missing_tickers)} tickers from configured provider ({provider.provider_name})...")

        try:
            batch_results = await provider.get_ticker_data_batch(missing_tickers)
            if batch_results:
                # Save successes to cache and results
                valid_batch_results = []
                for t, data in batch_results.items():
                    if data and data.exists and not math.isnan(data.price):
                        results[t] = data
                        valid_batch_results.append(data)
                        if t in missing_tickers:
                            missing_tickers.remove(t)

                if valid_batch_results:
                    self._save_batch_to_cache(valid_batch_results)
        except Exception as e:
            logger.error(f"Batch fetch failed for {provider.provider_name}: {e}")

        # 3. Final pass: resolve anything still missing individually.
        if missing_tickers:
            logger.info(f"Still missing {len(missing_tickers)} tickers after batch fetch. Trying individual retrieval...")
            for ticker in list(missing_tickers):
                data = await self.get_quote(ticker, force_refresh=force_refresh)
                if data:
                    results[ticker] = data
                    missing_tickers.remove(ticker)

        return results

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
            if (now - fetched_at).total_seconds() > self.cache_ttl_seconds:
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
        self._save_batch_to_cache([data])

    def _save_batch_to_cache(self, data_list: list[TickerData]):
        """Internal helper to upsert multiple data points into the cache and record price history."""
        try:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cache_payloads = []
            history_payloads = []

            for data in data_list:
                if math.isnan(data.price) or math.isnan(data.market_cap):
                    logger.warning(f"Skipping cache save for {data.ticker} due to NaN values.")
                    continue

                payload = {
                    "ticker": data.ticker,
                    "price": data.price,
                    "market_cap": data.market_cap,
                    "fetched_at": now_iso
                }
                cache_payloads.append(payload)
                history_payloads.append(payload)

            if cache_payloads:
                # Upsert into the cache
                self.client.table("market_data_cache").upsert(cache_payloads).execute()

            if history_payloads:
                # Insert into history table
                self.client.table("price_history").insert(history_payloads).execute()

        except Exception as e:
            tickers = [d.ticker for d in data_list]
            logger.error(f"Error saving market data batch for {tickers}: {e}")

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

        # 2. Fetch from the configured provider
        provider = self.provider
        if provider is None:
            logger.error(f"No financial provider configured for history retrieval for {ticker}.")
            return []

        logger.info(f"Fetching history for {ticker} from configured provider ({provider.provider_name})...")
        history = await provider.get_history(ticker, days)

        if history:
            # 3. Save to history table so it's available next time
            try:
                payloads = []
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
                    payloads.append(payload)
                
                if payloads:
                    # Batch upsert into price_history
                    self.client.table("price_history").upsert(payloads, on_conflict="ticker, fetched_at").execute()
            except Exception as e:
                logger.warning(f"Error saving historical data for {ticker} to cache: {e}")
            return history
            
        return []
