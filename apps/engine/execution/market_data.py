"""Market data manager with persistent caching.

This module provides the MarketDataManager class, which coordinates between
external financial APIs and a local database cache to optimize data retrieval.
"""

import datetime
import math

from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client

from .providers.base import FinancialProvider, TickerData
from .providers.factory import get_financial_provider


def _validate_date_coverage(rows: list, days_requested: int) -> tuple[bool, str]:
    """Validate that cached price history rows represent true historical data.

    Returns:
        tuple: (is_valid, reason) - is_valid is True if cache should be used
    """
    if not rows:
        return False, "no data"

    today = datetime.datetime.now(datetime.UTC).date().isoformat()
    distinct_dates = set()
    for row in rows:
        fetched_at = row.get("fetched_at", "")
        if fetched_at:
            date_part = fetched_at[:10]
            distinct_dates.add(date_part)

    distinct_count = len(distinct_dates)

    if distinct_count == 0:
        return False, "no valid dates"

    if all(d == today for d in distinct_dates):
        return False, f"all {distinct_count} rows from today"

    min_required_dates = max(2, math.ceil(days_requested / 2))
    if distinct_count < min_required_dates:
        return False, f"only {distinct_count} distinct dates, need {min_required_dates}"

    has_old_data = any(d != today for d in distinct_dates)
    if not has_old_data:
        return False, f"no historical data (all {distinct_count} dates are today)"

    # Check cache staleness: if the newest date in cache is > 4 calendar days old,
    # it's considered stale (e.g. over weekends/holidays is fine, but weeks is not).
    sorted_dates = sorted(list(distinct_dates), reverse=True)
    newest_date_str = sorted_dates[0]
    try:
        newest_date = datetime.date.fromisoformat(newest_date_str)
        today_date = datetime.datetime.now(datetime.UTC).date()
        age_days = (today_date - newest_date).days
        if age_days > 4:
            return False, f"cache is stale (newest entry from {newest_date_str} is {age_days} days old)"
    except Exception as e:
        logger.warning(f"Error validating price history cache staleness: {e}")

    return True, f"valid cache with {distinct_count} distinct dates"


class MarketDataManager:
    """Manages market data retrieval with a database-backed cache."""

    _market_status_cache: dict = {
        "is_open": None,
        "fetched_at": None,
        "ttl_seconds": 1800,  # 30 minutes
    }
    _market_status_lock = None

    # In-memory cache for screener results to avoid redundant API hits within a session
    _screener_cache: dict = {}

    def __init__(self, cache_ttl_seconds: int | None = None):
        import core.config as cfg

        self.client = get_supabase_client()
        self.cache_ttl_seconds = (
            cache_ttl_seconds if cache_ttl_seconds is not None else cfg.MARKET_DATA_CACHE_TTL_SECONDS
        )
        self.providers = [get_financial_provider(cfg.FINANCIAL_PROVIDER)]

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
        now = datetime.datetime.now(datetime.UTC)
        cache = MarketDataManager._market_status_cache

        if cache["fetched_at"] is not None:
            elapsed = (now - cache["fetched_at"]).total_seconds()
            if elapsed < cache["ttl_seconds"]:
                logger.debug(f"Using cached market status: {'OPEN' if cache['is_open'] else 'CLOSED'}")
                return cache["is_open"]

        if MarketDataManager._market_status_lock is None:
            import asyncio

            MarketDataManager._market_status_lock = asyncio.Lock()

        async with MarketDataManager._market_status_lock:
            # Recheck cache after acquiring lock
            if cache["fetched_at"] is not None:
                elapsed = (now - cache["fetched_at"]).total_seconds()
                if elapsed < cache["ttl_seconds"]:
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
                        url = "https://financialmodelingprep.com/stable/exchange-market-hours"
                        params = {"exchange": "NASDAQ", "apikey": FMP_API_KEY}
                        resp = await client.get(url, params=params)
                        resp.raise_for_status()
                        data = resp.json()

                        if data and isinstance(data, list):
                            is_open = data[0].get("isMarketOpen", False)
                            logger.info(f"FMP Market Status (NASDAQ): {'OPEN' if is_open else 'CLOSED'}")

                            # Fallback to time-based override for transient API cache lag right at market open
                            # (9:30 AM - 9:50 AM ET on weekdays)
                            if not is_open:
                                try:
                                    from zoneinfo import ZoneInfo

                                    now_et_check = datetime.datetime.now(ZoneInfo("America/New_York"))
                                except ImportError:
                                    now_et_check = datetime.datetime.now()

                                if now_et_check.weekday() < 5:
                                    market_open_threshold = now_et_check.replace(
                                        hour=9, minute=30, second=0, microsecond=0
                                    )
                                    buffer_end = now_et_check.replace(hour=9, minute=50, second=0, microsecond=0)
                                    if market_open_threshold <= now_et_check <= buffer_end:
                                        logger.info(
                                            "FMP reported CLOSED, but time is within the market-open buffer (9:30-9:50 AM ET) on a weekday. Overriding to OPEN."
                                        )
                                        is_open = True

                            # Cache the result
                            cache["is_open"] = is_open
                            cache["fetched_at"] = datetime.datetime.now(datetime.UTC)

                            return is_open
                except Exception as e:
                    logger.warning(f"Failed to fetch market status from FMP: {e}. Falling back to time-based check.")

            # 2. Fallback Check: Time-based (Mon-Fri, 09:30-16:00 ET)
            # Weekends
            if now_et.weekday() >= 5:  # 5=Sat, 6=Sun
                result = False
            else:
                market_start = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
                market_end = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
                result = market_start <= now_et <= market_end

            # Cache the fallback result as well
            cache["is_open"] = result
            cache["fetched_at"] = datetime.datetime.now(datetime.UTC)

            return result

    async def get_quote(self, ticker: str, force_refresh: bool = False) -> TickerData | None:
        """Fetch stock quote, checking cache first unless force_refresh is True.

        Args:
            ticker: The stock ticker symbol.
            force_refresh: Whether to bypass the cache and fetch fresh data.

        Returns:
            TickerData if found, None otherwise.
        """
        if not ticker or not isinstance(ticker, str):
            return None

        ticker = ticker.strip().upper()

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

    async def is_premarket(self) -> bool:
        """Checks if currently in US pre-market trading session (Mon-Fri 04:00 - 09:30 ET).

        Returns False on weekends.
        """
        import datetime

        try:
            from zoneinfo import ZoneInfo

            now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
        except ImportError:
            now_et = datetime.datetime.now()

        # Weekends
        if now_et.weekday() >= 5:
            return False

        premarket_start = now_et.replace(hour=4, minute=0, second=0, microsecond=0)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)

        return premarket_start <= now_et < market_open

    async def get_premarket_quote(self, ticker: str) -> dict | None:
        """Fetch fresh pre-market / early session quote and calculate change details vs previous close."""
        if not ticker or not isinstance(ticker, str):
            return None

        ticker = ticker.strip().upper()

        # 1. Try dedicated aftermarket / pre-market quote from provider if supported
        pm_price = None
        prev_close = None
        change = None
        change_pct = None
        volume = None

        provider = self.provider
        if provider and hasattr(provider, "get_aftermarket_quote"):
            try:
                aftermarket_quote = await provider.get_aftermarket_quote(ticker)
                if aftermarket_quote and aftermarket_quote.get("price") and float(aftermarket_quote["price"]) > 0:
                    pm_price = float(aftermarket_quote["price"])
                    volume = aftermarket_quote.get("volume")
            except Exception as e:
                logger.debug(f"Provider aftermarket quote lookup failed for {ticker}: {e}")

        # 2. Fall back to standard quote if aftermarket quote wasn't available
        quote = await self.get_quote(ticker, force_refresh=True)
        if quote:
            if pm_price is None and quote.price and quote.price > 0:
                pm_price = quote.price
                change = quote.change
                change_pct = quote.change_pct
                if volume is None:
                    volume = quote.volume
            if quote.previous_close and quote.previous_close > 0:
                prev_close = quote.previous_close

        if pm_price is None or pm_price <= 0:
            return None

        # 3. If previous close is still missing, fall back to recent history
        if prev_close is None or prev_close <= 0:
            history = await self.get_history(ticker, days=5)
            if history:
                sorted_hist = sorted(history, key=lambda x: x.get("fetched_at", ""))
                prev_close = float(sorted_hist[-1].get("close") or sorted_hist[-1].get("price"))

        if not prev_close or prev_close <= 0:
            prev_close = pm_price

        if change is None:
            change = pm_price - prev_close
        if change_pct is None:
            change_pct = (change / prev_close) * 100.0 if prev_close else 0.0

        res = {
            "price": pm_price,
            "previous_close": prev_close,
            "change": change,
            "change_pct": change_pct,
        }
        if volume is not None:
            res["volume"] = volume

        return res

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

        # Create a cache key from the parameters
        cache_key = f"{market_cap_more_than}-{market_cap_lower_than}-{price_more_than}-{price_lower_than}-{beta_more_than}-{beta_lower_than}-{volume_more_than}-{volume_lower_than}-{dividend_more_than}-{dividend_lower_than}-{sector}-{industry}-{exchange}-{limit}-{is_actively_trading}"

        if cache_key in MarketDataManager._screener_cache:
            logger.debug(f"Returning cached screener results for key: {cache_key[:30]}...")
            return MarketDataManager._screener_cache[cache_key]

        # Currently only FMP supports direct screening tool
        provider = self.provider  # Primary provider
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
                is_actively_trading=is_actively_trading,
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

        tickers = [t.strip().upper() for t in tickers]
        results = {}
        missing_tickers = list(tickers)

        # 1. Check Cache
        if not force_refresh:
            try:
                response = self.client.table("market_data_cache").select("*").in_("ticker", tickers).execute()
                if response.data:
                    now = datetime.datetime.now(datetime.UTC)
                    for record in response.data:
                        ticker = record["ticker"]
                        fetched_at = datetime.datetime.fromisoformat(record["fetched_at"].replace("Z", "+00:00"))
                        if (now - fetched_at).total_seconds() <= self.cache_ttl_seconds:
                            results[ticker] = TickerData(
                                ticker=ticker,
                                price=float(record["price"]),
                                market_cap=float(record["market_cap"]) if record.get("market_cap") else 0,
                                exists=True,
                            )
                            if ticker in missing_tickers:
                                missing_tickers.remove(ticker)
                        else:
                            logger.debug(f"Cache entry for {ticker} is stale.")
            except Exception as e:
                logger.error(f"Error reading market data cache batch: {e}")

        if not missing_tickers:
            return results

        # 2. Fetch missing from the configured provider
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
        import asyncio

        from core.config import MARKET_DATA_RETRIES

        for attempt in range(1, MARKET_DATA_RETRIES + 1):
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
                # Reduce noise: don't log full stack trace for common timeouts/connection errors
                logger.debug(
                    f"Attempt {attempt}/{MARKET_DATA_RETRIES} failed for {ticker} via {provider.provider_name}: {e}"
                )

            if attempt < MARKET_DATA_RETRIES:
                wait_time = 2 ** (attempt - 1)
                await asyncio.sleep(wait_time)
        return None

    def _get_last_known_price(self, ticker: str) -> TickerData | None:
        """Retrieves the most recent price from the history table with a 24h staleness check."""
        try:
            # We want the latest entry from price_history
            response = (
                self.client.table("price_history")
                .select("*")
                .eq("ticker", ticker)
                .order("fetched_at", desc=True)
                .limit(1)
                .execute()
            )

            if response.data:
                record = response.data[0]
                fetched_at_str = record.get("fetched_at", "")
                if fetched_at_str:
                    try:
                        from dateutil import parser

                        fetched_at = parser.isoparse(fetched_at_str)
                        if fetched_at.tzinfo is None:
                            fetched_at = fetched_at.replace(tzinfo=datetime.UTC)

                        now = datetime.datetime.now(datetime.UTC)
                        age_hours = (now - fetched_at).total_seconds() / 3600

                        if age_hours > 24:
                            logger.warning(f"Last known price for {ticker} is stale ({age_hours:.1f}h old). Rejecting.")
                            return None
                    except Exception as parse_err:
                        logger.error(f"Error parsing fetched_at for {ticker}: {parse_err}")
                        return None

                return TickerData(
                    ticker=record["ticker"],
                    price=float(record["price"]),
                    market_cap=float(record["market_cap"]) if record.get("market_cap") else 0,
                    exists=True,
                )
        except Exception as e:
            logger.error(f"Error fetching last known price for {ticker}: {e}")

        return None

    def _get_from_cache(self, ticker: str) -> TickerData | None:
        """Internal helper to retrieve and validate cached data."""
        try:
            response = self.client.table("market_data_cache").select("*").eq("ticker", ticker).execute()

            if not response.data:
                return None

            record = response.data[0]
            fetched_at = datetime.datetime.fromisoformat(record["fetched_at"].replace("Z", "+00:00"))
            now = datetime.datetime.now(datetime.UTC)

            # Check if cache is stale
            if (now - fetched_at).total_seconds() > self.cache_ttl_seconds:
                logger.debug(f"Cache entry for {ticker} is stale.")
                return None

            return TickerData(
                ticker=record["ticker"],
                price=float(record["price"]),
                market_cap=float(record["market_cap"]) if record.get("market_cap") else 0,
                exists=True,
            )
        except Exception as e:
            logger.error(f"Error reading market data cache for {ticker}: {e}")
            return None

    def _save_to_cache(self, data: TickerData):
        """Internal helper to upsert data into the live price cache."""
        self._save_batch_to_cache([data])

    def _save_batch_to_cache(self, data_list: list[TickerData]):
        """Internal helper to upsert multiple data points into the live price cache.

        Note: EOD historical data is stored separately via get_history() to avoid
        crowding out true historical records with high-frequency batch snapshots.
        """
        try:
            now_iso = datetime.datetime.now(datetime.UTC).isoformat()
            cache_payloads = []

            for data in data_list:
                if math.isnan(data.price) or math.isnan(data.market_cap):
                    logger.warning(f"Skipping cache save for {data.ticker} due to NaN values.")
                    continue

                payload = {
                    "ticker": data.ticker.strip(),
                    "price": data.price,
                    "market_cap": data.market_cap,
                    "fetched_at": now_iso,
                }
                cache_payloads.append(payload)

            if cache_payloads:
                # Upsert into the cache
                self.client.table("market_data_cache").upsert(cache_payloads).execute()

        except Exception as e:
            tickers = [d.ticker for d in data_list]
            logger.error(f"Error saving market data batch for {tickers}: {e}")

    async def get_history(self, ticker: str, days: int = 14, force_refresh: bool = False) -> list[dict]:
        """Fetch historical price data, checking local DB first.

        Args:
            ticker: The stock ticker symbol.
            days: Number of days of history to retrieve.
            force_refresh: Whether to bypass the local DB cache.

        Returns:
            List of dicts with 'price' and 'fetched_at'.
        """
        ticker = ticker.strip().upper()

        # 1. Check local DB (unless force_refresh is True)
        if not force_refresh:
            try:
                res = (
                    self.client.table("price_history")
                    .select("price, open, high, low, close, fetched_at")
                    .eq("ticker", ticker)
                    .order("fetched_at", desc=True)
                    .limit(days)
                    .execute()
                )

                if res.data and len(res.data) >= (days * 0.7):
                    is_valid, reason = _validate_date_coverage(res.data, days)
                    if is_valid:
                        logger.debug(f"Using local price history for {ticker} ({len(res.data)} samples, {reason}).")
                        return [
                            {
                                "price": float(row["price"]),
                                "open": float(row["open"]) if row.get("open") is not None else None,
                                "high": float(row["high"]) if row.get("high") is not None else None,
                                "low": float(row["low"]) if row.get("low") is not None else None,
                                "close": float(row["close"]) if row.get("close") is not None else None,
                                "fetched_at": row["fetched_at"],
                            }
                            for row in res.data
                        ]
                    else:
                        logger.debug(f"Skipping local cache for {ticker}: {reason}. Fetching from provider.")
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
                    payload = {
                        "ticker": ticker,
                        "price": float(entry["price"]),
                        "fetched_at": entry["fetched_at"],
                        "market_cap": entry.get("market_cap", 0),  # Fallback for non-null column
                    }
                    # Persist OHLC when available so fetch_intraday_prices() can
                    # compute correct intraday hit metrics on subsequent reads.
                    if entry.get("open") is not None:
                        payload["open"] = float(entry["open"])
                    if entry.get("high") is not None:
                        payload["high"] = float(entry["high"])
                    if entry.get("low") is not None:
                        payload["low"] = float(entry["low"])
                    if entry.get("close") is not None:
                        payload["close"] = float(entry["close"])
                    elif entry.get("price") is not None:
                        payload["close"] = float(entry["price"])  # price == close for EOD bars
                    payloads.append(payload)

                if payloads:
                    # Batch upsert into price_history
                    self.client.table("price_history").upsert(payloads, on_conflict="ticker, fetched_at").execute()
            except Exception as e:
                logger.warning(f"Error saving historical data for {ticker} to cache: {e}")
            return history

        return []

    async def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 1) -> list[dict]:
        """Fetch fundamental financial key metrics for a ticker.

        Delegates to the configured financial provider.
        """
        provider = self.provider
        if provider is None:
            logger.error(f"No financial provider configured for key metrics retrieval for {ticker}.")
            return []

        return await provider.get_key_metrics(ticker, period, limit)

    async def get_earnings_history(self, ticker: str, limit: int = 8) -> list[dict]:
        """Fetch historical earnings and upcoming date for a ticker.

        Delegates to the configured financial provider.
        """
        provider = self.provider
        if provider is None:
            logger.error(f"No financial provider configured for earnings history retrieval for {ticker}.")
            return []

        return await provider.get_earnings_history(ticker, limit)

    async def get_analyst_estimates(self, ticker: str, period: str = "annual", limit: int = 5) -> list[dict]:
        """Fetch forward analyst consensus estimates for a ticker.

        Delegates to the configured financial provider.
        """
        provider = self.provider
        if provider is None:
            logger.error(f"No financial provider configured for analyst estimates retrieval for {ticker}.")
            return []

        # Some providers might not implement it dynamically, check before calling
        if not hasattr(provider, "get_analyst_estimates"):
            logger.warning(f"Provider {provider.provider_name} does not support analyst estimates.")
            return []

        return await provider.get_analyst_estimates(ticker, period, limit)

    async def get_financial_growth(self, ticker: str, period: str = "annual", limit: int = 5) -> list[dict]:
        """Fetch historical financial growth metrics (YoY) for a ticker.

        Delegates to the configured financial provider.
        """
        provider = self.provider
        if provider is None:
            logger.error(f"No financial provider configured for financial growth retrieval for {ticker}.")
            return []

        if not hasattr(provider, "get_financial_growth"):
            logger.warning(f"Provider {provider.provider_name} does not support financial growth.")
            return []

        return await provider.get_financial_growth(ticker, period, limit)

    async def get_company_profile(self, ticker: str) -> list[dict]:
        """Fetch company profile (including beta, sector, shares outstanding) for a ticker.

        Delegates to the configured financial provider.
        """
        provider = self.provider
        if provider is None:
            logger.error(f"No financial provider configured for company profile retrieval for {ticker}.")
            return []

        if not hasattr(provider, "get_company_profile"):
            logger.warning(f"Provider {provider.provider_name} does not support company profile.")
            return []

        return await provider.get_company_profile(ticker)
