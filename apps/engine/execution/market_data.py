"""Market data manager with persistent caching.

Coordinates external financial providers, persistent database caching, market session schedules,
and data transforms through a modular, unified facade.
"""

import asyncio
import math

import core.config as cfg
from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client

from .market_cache import MarketDataCache
from .market_session import MarketSessionManager
from .market_transforms import compute_premarket_quote, validate_date_coverage
from .providers.base import FinancialProvider, TickerData
from .providers.factory import get_financial_provider

# Backward compatibility alias for legacy imports/tests
_validate_date_coverage = validate_date_coverage
MARKET_DATA_RETRIES = getattr(cfg, "MARKET_DATA_RETRIES", 2)


class MarketDataManager:
    """Manages market data retrieval with database-backed caching and provider fallback."""

    _market_status_cache: dict = MarketSessionManager._market_status_cache
    _market_status_lock: asyncio.Lock | None = None

    _holidays_cache: dict = MarketSessionManager._holidays_cache
    _holidays_lock: asyncio.Lock | None = None

    _screener_cache: dict = {}

    def __init__(self, cache_ttl_seconds: int | None = None):
        self._client = get_supabase_client()
        self._cache_ttl_seconds = (
            cache_ttl_seconds if cache_ttl_seconds is not None else cfg.MARKET_DATA_CACHE_TTL_SECONDS
        )
        self.cache = MarketDataCache(client=self._client, cache_ttl_seconds=self._cache_ttl_seconds)
        self.session = MarketSessionManager(fmp_api_key=FMP_API_KEY)
        self.providers = [get_financial_provider(cfg.FINANCIAL_PROVIDER)]

    @property
    def client(self):
        """Getter for Supabase client."""
        return self._client

    @client.setter
    def client(self, value):
        """Setter to allow manual override of Supabase client."""
        self._client = value
        if hasattr(self, "cache"):
            self.cache.client = value

    @property
    def cache_ttl_seconds(self):
        """Getter for cache TTL in seconds."""
        return self._cache_ttl_seconds

    @cache_ttl_seconds.setter
    def cache_ttl_seconds(self, value):
        """Setter to allow manual override of cache TTL."""
        self._cache_ttl_seconds = value
        if hasattr(self, "cache"):
            self.cache.cache_ttl_seconds = value

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
        """Checks if the US stock market (NASDAQ/NYSE) is currently open."""
        self.session._market_status_cache = MarketDataManager._market_status_cache
        if MarketDataManager._market_status_lock is not None:
            MarketSessionManager._market_status_lock = MarketDataManager._market_status_lock

        is_open = await self.session.is_market_open(fmp_api_key=FMP_API_KEY)
        MarketDataManager._market_status_cache = self.session._market_status_cache
        MarketDataManager._market_status_lock = MarketSessionManager._market_status_lock
        return is_open

    async def get_market_holidays(self) -> list[dict]:
        """Fetch US market holidays from FMP API with in-memory caching."""
        self.session._holidays_cache = MarketDataManager._holidays_cache
        if MarketDataManager._holidays_lock is not None:
            MarketSessionManager._holidays_lock = MarketDataManager._holidays_lock

        holidays = await self.session.get_market_holidays(fmp_api_key=FMP_API_KEY)
        MarketDataManager._holidays_cache = self.session._holidays_cache
        MarketDataManager._holidays_lock = MarketSessionManager._holidays_lock
        return holidays

    def _is_known_us_market_holiday_fallback(self, date_obj) -> bool:
        """Rule-based fallback for US stock exchange holidays when API data is unavailable."""
        return MarketSessionManager.is_known_us_market_holiday_fallback(date_obj)

    async def is_trading_day(self, target_date=None) -> bool:
        """Checks if a given date is an active US equity trading day (non-weekend, non-holiday)."""
        return await self.session.is_trading_day(target_date=target_date, fmp_api_key=FMP_API_KEY)

    async def is_premarket(self) -> bool:
        """Checks if currently in US pre-market trading session (Mon-Fri 04:00 - 09:30 ET)."""
        return await MarketSessionManager.is_premarket()

    async def get_quote(self, ticker: str, force_refresh: bool = False) -> TickerData | None:
        """Fetch stock quote, checking cache first unless force_refresh is True."""
        if not ticker or not isinstance(ticker, str):
            return None

        ticker = ticker.strip().upper()

        # 1. Check Cache
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
            self._save_to_cache(data)
            return data

        # 3. Fallback: Last Known Price from History (24h staleness check)
        last_known = self._get_last_known_price(ticker)
        if last_known:
            logger.info(f"All online retrieval failed for {ticker}. Using last known price: ${last_known.price}")
            return last_known

        logger.error(f"FATAL: All retrieval attempts failed for {ticker}. No historical data available.")
        return None

    async def get_premarket_quote(self, ticker: str) -> dict | None:
        """Fetch fresh pre-market / early session quote and calculate change details vs previous close."""
        if not ticker or not isinstance(ticker, str):
            return None

        ticker = ticker.strip().upper()

        # 1. Dedicated aftermarket quote lookup
        aftermarket_quote = None
        provider = self.provider
        if provider and hasattr(provider, "get_aftermarket_quote"):
            try:
                aftermarket_quote = await provider.get_aftermarket_quote(ticker)
            except Exception as e:
                logger.debug(f"Provider aftermarket quote lookup failed for {ticker}: {e}")

        # 2. Standard quote lookup
        quote = await self.get_quote(ticker, force_refresh=True)

        # 3. History fallback if previous close is missing
        history = None
        needs_history_fallback = not quote or not (quote.price or quote.previous_close)
        if needs_history_fallback or (quote and not quote.previous_close and aftermarket_quote is None):
            history = await self.get_history(ticker, days=5)

        return compute_premarket_quote(
            quote=quote,
            aftermarket_quote=aftermarket_quote,
            history=history,
        )

    async def get_quotes(self, tickers: list[str], force_refresh: bool = False) -> dict[str, TickerData]:
        """Fetch multiple stock quotes, checking cache first where possible."""
        if not tickers:
            return {}

        tickers = [t.strip().upper() for t in tickers]
        results = {}
        missing_tickers = list(tickers)

        # 1. Check Cache
        if not force_refresh:
            cached_results, missing_tickers = self.cache.get_quotes_batch(tickers)
            results.update(cached_results)

        if not missing_tickers:
            return results

        # 2. Fetch missing from configured provider
        provider = self.provider
        if provider is None:
            logger.error("No financial provider configured for batch quote retrieval.")
            return results

        logger.info(
            f"Batch fetching {len(missing_tickers)} tickers from configured provider ({provider.provider_name})..."
        )

        try:
            batch_results = await provider.get_ticker_data_batch(missing_tickers)
            if batch_results:
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

        # 3. Final individual pass for remaining missing tickers
        if missing_tickers:
            logger.info(
                f"Still missing {len(missing_tickers)} tickers after batch fetch. Trying individual retrieval..."
            )
            for ticker in list(missing_tickers):
                data = await self.get_quote(ticker, force_refresh=force_refresh)
                if data:
                    results[ticker] = data
                    missing_tickers.remove(ticker)

        return results

    async def _fetch_with_backoff(self, provider: FinancialProvider, ticker: str) -> TickerData | None:
        """Helper to fetch data from a provider with retries and validation."""
        max_retries = getattr(cfg, "MARKET_DATA_RETRIES", MARKET_DATA_RETRIES)
        for attempt in range(1, max_retries + 1):
            try:
                data = await provider.get_ticker_data(ticker)
                if data and data.exists:
                    if math.isnan(data.price):
                        logger.warning(
                            f"Provider {provider.provider_name} returned NaN price for {ticker}. Proceeding..."
                        )
                        continue
                    return data
            except Exception as e:
                logger.debug(f"Attempt {attempt}/{max_retries} failed for {ticker} via {provider.provider_name}: {e}")

            if attempt < max_retries:
                wait_time = 2 ** (attempt - 1)
                await asyncio.sleep(wait_time)
        return None

    def _get_from_cache(self, ticker: str) -> TickerData | None:
        """Internal helper to retrieve cached data."""
        return self.cache.get_quote(ticker)

    def _save_to_cache(self, data: TickerData) -> None:
        """Internal helper to upsert data into the live price cache."""
        self.cache.save_quote(data)

    def _save_batch_to_cache(self, data_list: list[TickerData]) -> None:
        """Internal helper to upsert multiple data points into the live price cache."""
        self.cache.save_quotes_batch(data_list)

    def _get_last_known_price(self, ticker: str) -> TickerData | None:
        """Retrieves the most recent price from the history table with a 24h staleness check."""
        return self.cache.get_last_known_price(ticker)

    async def get_history(self, ticker: str, days: int = 14, force_refresh: bool = False) -> list[dict]:
        """Fetch historical price data, checking local DB first."""
        ticker = ticker.strip().upper()

        # 1. Check local DB
        if not force_refresh:
            cached_history = self.cache.get_history(ticker, days=days)
            if cached_history is not None:
                return cached_history

        # 2. Fetch from configured provider
        provider = self.provider
        if provider is None:
            logger.error(f"No financial provider configured for history retrieval for {ticker}.")
            return []

        logger.info(f"Fetching history for {ticker} from configured provider ({provider.provider_name})...")
        history = await provider.get_history(ticker, days)

        if history:
            self.cache.save_history(ticker, history)
            return history

        return []

    async def screen_stocks(
        self,
        market_cap_more_than: float | None = None,
        market_cap_lower_than: float | None = None,
        price_more_than: float | None = None,
        price_lower_than: float | None = None,
        beta_more_than: float | None = None,
        beta_lower_than: float | None = None,
        volume_more_than: float | None = None,
        volume_lower_than: float | None = None,
        dividend_more_than: float | None = None,
        dividend_lower_than: float | None = None,
        sector: str | None = None,
        industry: str | None = None,
        exchange: str | None = "NYSE,NASDAQ",
        limit: int = 10,
        is_actively_trading: bool = True,
    ) -> list[dict]:
        """Exposes stock screening capabilities, checking cache first."""
        params = {
            "market_cap_more_than": market_cap_more_than,
            "market_cap_lower_than": market_cap_lower_than,
            "price_more_than": price_more_than,
            "price_lower_than": price_lower_than,
            "beta_more_than": beta_more_than,
            "beta_lower_than": beta_lower_than,
            "volume_more_than": volume_more_than,
            "volume_lower_than": volume_lower_than,
            "dividend_more_than": dividend_more_than,
            "dividend_lower_than": dividend_lower_than,
            "sector": sector,
            "industry": industry,
            "exchange": exchange,
            "limit": limit,
            "is_actively_trading": is_actively_trading,
        }
        cache_key = str(sorted(params.items()))
        if cache_key in MarketDataManager._screener_cache:
            return MarketDataManager._screener_cache[cache_key]

        provider = self.provider
        if not hasattr(provider, "screen_stocks"):
            logger.error(f"Primary provider {provider.provider_name} does not support screening.")
            return []

        try:
            results = await provider.screen_stocks(**params)
            MarketDataManager._screener_cache[cache_key] = results
            return results
        except Exception as e:
            logger.error(f"Error executing stock screen via {provider.provider_name}: {e}")
            return []

    def _require_provider(self, ticker: str) -> FinancialProvider | None:
        provider = self.provider
        if provider is None:
            logger.error(f"No financial provider configured for {ticker}.")
        return provider

    async def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 1) -> list[dict]:
        """Fetch fundamental financial key metrics for a ticker."""
        p = self._require_provider(ticker)
        return await p.get_key_metrics(ticker, period, limit) if p else []

    async def get_earnings_history(self, ticker: str, limit: int = 8) -> list[dict]:
        """Fetch historical earnings and upcoming date for a ticker."""
        p = self._require_provider(ticker)
        return await p.get_earnings_history(ticker, limit) if p else []

    async def get_analyst_estimates(self, ticker: str, period: str = "annual", limit: int = 5) -> list[dict]:
        """Fetch forward analyst consensus estimates for a ticker."""
        p = self._require_provider(ticker)
        if not p or not hasattr(p, "get_analyst_estimates"):
            return []
        return await p.get_analyst_estimates(ticker, period, limit)

    async def get_financial_growth(self, ticker: str, period: str = "annual", limit: int = 5) -> list[dict]:
        """Fetch historical financial growth metrics (YoY) for a ticker."""
        p = self._require_provider(ticker)
        if not p or not hasattr(p, "get_financial_growth"):
            return []
        return await p.get_financial_growth(ticker, period, limit)

    async def get_company_profile(self, ticker: str) -> list[dict]:
        """Fetch company profile (including beta, sector, shares outstanding) for a ticker."""
        p = self._require_provider(ticker)
        if not p or not hasattr(p, "get_company_profile"):
            return []
        return await p.get_company_profile(ticker)
