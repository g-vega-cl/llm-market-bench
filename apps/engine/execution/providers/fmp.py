"""Financial Modeling Prep (FMP) implementation of FinancialProvider."""

import asyncio
import os
import sqlite3
import time
from datetime import datetime, timedelta

import httpx

from core.config import FMP_API_KEY, MARKET_DATA_RETRIES, logger

from .base import FinancialProvider, HistoryData, HourlyBar, TickerData

FMP_TIMEOUT = httpx.Timeout(10.0)


class FMPProvider(FinancialProvider):
    """Provider for Financial Modeling Prep API."""

    BASE_URL = "https://financialmodelingprep.com/stable"
    _last_call_time = 0.0  # Shared across all instances to throttle globally
    _db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".hourly_price_cache.db"
    )

    def __init__(self):
        if not FMP_API_KEY:
            logger.warning("FMP_API_KEY not found in environment. FMP validation will be disabled.")
        self.api_key = FMP_API_KEY
        self._init_db()

    def _init_db(self):
        """Initialize the local SQLite cache for hourly bars."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hourly_bars (
                    ticker TEXT,
                    bar_date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    PRIMARY KEY (ticker, bar_date)
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite hourly price cache database: {e}")

    async def get_ticker_data(self, ticker: str) -> TickerData | None:
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

        for attempt in range(1, MARKET_DATA_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                    # 1. Get Consolidated Quote (Price + Market Cap)
                    quote_resp = await client.get(
                        f"{self.BASE_URL}/quote", params={"symbol": ticker, "apikey": self.api_key}
                    )
                    quote_resp.raise_for_status()
                    quote_data = quote_resp.json()

                    if not quote_data:
                        logger.warning(f"Ticker {ticker} not found on FMP.")
                        return None

                    # Verify ticker match to handle potential FMP list shifting/search-like behavior
                    q = None
                    for candidate in quote_data:
                        if str(candidate.get("symbol")).upper() == ticker.upper():
                            q = candidate
                            break

                    if q is None:
                        logger.warning(
                            f"FMP returned data but none matched requested ticker {ticker}. Response: {quote_data[:1]}"
                        )
                        return None

                    return TickerData(
                        ticker=ticker,
                        price=float(q.get("price", 0)),
                        market_cap=float(q.get("marketCap", 0)),
                        exists=True,
                        currency=q.get("currency", "USD"),
                        exchange=q.get("exchange"),
                    )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 402:
                    logger.error(f"FMP API Quota Exceeded (402 Payment Required): {e.response.url}")
                    return None  # Don't retry quota errors
                logger.error(
                    f"HTTP error fetching data from FMP for {ticker}: "
                    f"status={e.response.status_code}, "
                    f"response={e.response.text[:500] if e.response.text else 'empty'}, "
                    f"error={repr(e)}"
                )
            except Exception as e:
                error_details = f"{e} ({repr(e)})" if str(e) else repr(e)
                logger.warning(f"Attempt {attempt}/{MARKET_DATA_RETRIES} failed for {ticker} via FMP: {error_details}")

            if attempt < MARKET_DATA_RETRIES:
                wait_time = 2 ** (attempt - 1)
                await asyncio.sleep(wait_time)

        logger.error(f"All {MARKET_DATA_RETRIES} attempts failed for {ticker} via FMP.")
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

    async def get_history(self, ticker: str, days: int = 14) -> list[HistoryData]:
        """Fetch historical price data with volume using FMP."""
        if not self.api_key:
            return []

        # Calculate calendar date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        from_str = start_date.strftime("%Y-%m-%d")
        to_str = end_date.strftime("%Y-%m-%d")

        for attempt in range(1, MARKET_DATA_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                    resp = await client.get(
                        f"{self.BASE_URL}/historical-price-eod/full",
                        params={"symbol": ticker, "from": from_str, "to": to_str, "apikey": self.api_key},
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    historical_data = data if isinstance(data, list) else data.get("historical", [])

                    if not historical_data:
                        logger.warning(f"No history found for {ticker} on FMP.")
                        return []

                    results = []
                    for entry in historical_data:
                        results.append(
                            HistoryData(
                                price=float(entry["close"]), volume=entry.get("volume"), fetched_at=entry["date"]
                            )
                        )

                    return results

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 402:
                    logger.error(f"FMP API Quota Exceeded (402 Payment Required) for {ticker} history")
                    return []
                logger.error(
                    f"HTTP error fetching history from FMP for {ticker}: "
                    f"status={e.response.status_code}, error={repr(e)}"
                )
            except Exception as e:
                error_details = f"{e} ({repr(e)})" if str(e) else repr(e)
                logger.warning(
                    f"Attempt {attempt}/{MARKET_DATA_RETRIES} failed fetching history for {ticker} via FMP: {error_details}"
                )

            if attempt < MARKET_DATA_RETRIES:
                wait_time = 2 ** (attempt - 1)
                await asyncio.sleep(wait_time)

        logger.error(f"All {MARKET_DATA_RETRIES} attempts failed fetching history for {ticker} via FMP.")
        return []

    async def search_tickers(self, query: str, limit: int = 5) -> list[dict]:
        """Search for tickers by name or symbol using FMP."""
        if not self.api_key:
            return []

        try:
            async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/search-symbol", params={"query": query, "limit": limit, "apikey": self.api_key}
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            error_details = f"{e} ({repr(e)})" if str(e) else repr(e)
            logger.error(f"Error searching tickers on FMP for '{query}': {error_details}")
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
        """Screen stocks using FMP /company-screener with advanced filters."""
        if not self.api_key:
            return []

        # Construction of parameters for FMP API
        # Mapping our snake_case snake_case to FMP's camelCase
        params = {
            "limit": min(limit, 15),  # Cap at 15 for context efficiency
            "apikey": self.api_key,
            "isActivelyTrading": str(is_actively_trading).lower(),
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
            async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                resp = await client.get(f"{self.BASE_URL}/company-screener", params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            error_details = f"{e} ({repr(e)})" if str(e) else repr(e)
            logger.error(f"Error screening stocks on FMP: {error_details}")
            return []

    async def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 1) -> list[dict]:
        """Fetch fundamental financial key metrics for a ticker from FMP."""
        if not self.api_key:
            return []

        try:
            async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                # Build params with symbol instead of ticker path for stable API
                params = {
                    "symbol": ticker,
                    "period": period,
                    "limit": limit,
                    "apikey": self.api_key,
                }

                # Fetch key-metrics and ratios in parallel
                metrics_task = client.get(f"{self.BASE_URL}/key-metrics", params=params)
                ratios_task = client.get(f"{self.BASE_URL}/ratios", params=params)

                metrics_resp, ratios_resp = await asyncio.gather(metrics_task, ratios_task)

                # Fallback to annual if quarterly is not supported (e.g. 402/403 or non-200)
                if period == "quarter" and (metrics_resp.status_code != 200 or ratios_resp.status_code != 200):
                    logger.warning(
                        f"FMP quarterly metrics not available for {ticker} (status {metrics_resp.status_code}/{ratios_resp.status_code}). "
                        "Retrying with period='annual'..."
                    )
                    params["period"] = "annual"
                    metrics_task = client.get(f"{self.BASE_URL}/key-metrics", params=params)
                    ratios_task = client.get(f"{self.BASE_URL}/ratios", params=params)
                    metrics_resp, ratios_resp = await asyncio.gather(metrics_task, ratios_task)

                # If both attempts failed (e.g. 402 on both quarterly and annual), return empty
                if metrics_resp.status_code != 200 or ratios_resp.status_code != 200:
                    logger.warning(
                        f"FMP key metrics unavailable for {ticker} "
                        f"(metrics={metrics_resp.status_code}, ratios={ratios_resp.status_code}). "
                        "Skipping."
                    )
                    return []

                metrics_resp.raise_for_status()
                ratios_resp.raise_for_status()

                metrics_data = metrics_resp.json()
                ratios_data = ratios_resp.json()

                merged_by_date = {}

                # Process metrics
                if isinstance(metrics_data, list):
                    for entry in metrics_data:
                        date = entry.get("date")
                        if not date:
                            continue

                        merged_by_date[date] = {
                            "symbol": entry.get("symbol") or ticker,
                            "date": date,
                            "calendarYear": entry.get("fiscalYear") or entry.get("calendarYear"),
                            "period": entry.get("period"),
                            "enterpriseValueOverEBITDA": entry.get("evToEBITDA"),
                            "freeCashFlowYield": entry.get("freeCashFlowYield"),
                            "netDebt": entry.get("netDebt"),
                            "marketCap": entry.get("marketCap"),
                            "enterpriseValue": entry.get("enterpriseValue"),
                        }

                # Process ratios
                if isinstance(ratios_data, list):
                    for entry in ratios_data:
                        date = entry.get("date")
                        if not date:
                            continue

                        if date not in merged_by_date:
                            merged_by_date[date] = {
                                "symbol": entry.get("symbol") or ticker,
                                "date": date,
                                "calendarYear": entry.get("fiscalYear") or entry.get("calendarYear"),
                                "period": entry.get("period"),
                            }

                        merged_by_date[date].update(
                            {
                                "peRatio": entry.get("priceToEarningsRatio"),
                                "priceToSalesRatio": entry.get("priceToSalesRatio"),
                                "pbRatio": entry.get("priceToBookRatio"),
                                "debtToEquity": entry.get("debtToEquityRatio"),
                                "currentRatio": entry.get("currentRatio"),
                                "roe": entry.get("returnOnEquity"),
                                "dividendYield": entry.get("dividendYield"),
                                "bookValuePerShare": entry.get("bookValuePerShare"),
                                "revenuePerShare": entry.get("revenuePerShare"),
                                "netIncomePerShare": entry.get("netIncomePerShare"),
                                "freeCashFlowPerShare": entry.get("freeCashFlowPerShare"),
                            }
                        )

                # Sort by date descending
                sorted_dates = sorted(merged_by_date.keys(), reverse=True)
                results = [merged_by_date[d] for d in sorted_dates[:limit]]
                for entry in results:
                    fcf_yield = entry.get("freeCashFlowYield")
                    if fcf_yield is not None:
                        try:
                            fcf_yield_val = float(fcf_yield)
                            if fcf_yield_val != 0:
                                entry["priceToFreeCashFlowsRatio"] = 1.0 / fcf_yield_val
                        except (ValueError, TypeError):
                            pass
                return results

        except Exception as e:
            error_details = f"{e} ({repr(e)})" if str(e) else repr(e)
            logger.error(f"Error fetching key metrics from FMP for {ticker}: {error_details}")
            return []

    async def get_earnings_history(self, ticker: str, limit: int = 8) -> list[dict]:
        """Fetch historical earnings estimates vs actuals and upcoming date using FMP."""
        if not self.api_key:
            return []

        try:
            async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                resp = await client.get(f"{self.BASE_URL}/earnings", params={"symbol": ticker, "apikey": self.api_key})
                resp.raise_for_status()
                data = resp.json()

                if not data or not isinstance(data, list):
                    return []

                results = []
                now_str = datetime.now().strftime("%Y-%m-%d")

                for entry in data[:limit]:
                    date_str = entry.get("date")
                    eps_actual = entry.get("epsActual")
                    eps_estimated = entry.get("epsEstimated")
                    revenue_actual = entry.get("revenueActual")
                    revenue_estimated = entry.get("revenueEstimated")

                    if eps_actual == "":
                        eps_actual = None
                    if eps_estimated == "":
                        eps_estimated = None
                    if revenue_actual == "":
                        revenue_actual = None
                    if revenue_estimated == "":
                        revenue_estimated = None

                    # Compute surprise percentage
                    surprise_pct = None
                    if eps_actual is not None and eps_estimated is not None and eps_estimated != 0:
                        surprise_pct = ((float(eps_actual) - float(eps_estimated)) / abs(float(eps_estimated))) * 100

                    results.append(
                        {
                            "symbol": ticker.upper(),
                            "date": date_str,
                            "epsActual": float(eps_actual) if eps_actual is not None else None,
                            "epsEstimated": float(eps_estimated) if eps_estimated is not None else None,
                            "revenueActual": float(revenue_actual) if revenue_actual is not None else None,
                            "revenueEstimated": float(revenue_estimated) if revenue_estimated is not None else None,
                            "surprisePct": surprise_pct,
                            "isUpcoming": eps_actual is None and date_str >= now_str,
                        }
                    )
                return results
        except Exception as e:
            logger.error(f"Error fetching earnings history from FMP for {ticker}: {e}")
            return []

    async def get_analyst_estimates(self, ticker: str, period: str = "annual", limit: int = 5) -> list[dict]:
        """Fetch forward analyst consensus estimates for a ticker from FMP."""
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/analyst-estimates",
                    params={"symbol": ticker, "period": period, "limit": limit, "apikey": self.api_key},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Error fetching analyst estimates from FMP for {ticker}: {e}")
            return []

    async def get_company_profile(self, ticker: str) -> list[dict]:
        """Fetch company profile (including beta, sector, shares outstanding) from FMP."""
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/profile",
                    params={"symbol": ticker, "apikey": self.api_key},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Error fetching company profile from FMP for {ticker}: {e}")
            return []

    async def get_financial_growth(self, ticker: str, period: str = "annual", limit: int = 5) -> list[dict]:
        """Fetch historical financial growth metrics (YoY) for a ticker from FMP."""
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/financial-growth",
                    params={"symbol": ticker, "period": period, "limit": limit, "apikey": self.api_key},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Error fetching financial growth from FMP for {ticker}: {e}")
            return []

    async def get_sp500_constituents(self) -> list[str]:
        """Fetch list of S&P 500 constituent symbols from FMP."""
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                resp = await client.get(f"{self.BASE_URL}/sp500-constituent", params={"apikey": self.api_key})
                resp.raise_for_status()
                data = resp.json()
                return [item["symbol"] for item in data if "symbol" in item]
        except Exception as e:
            logger.warning(f"Failed to fetch S&P 500 constituents dynamically (expected if free key): {e}")
            return []

    def _get_cached_hourly_bars(self, ticker: str, from_date: str, to_date: str) -> list[HourlyBar]:
        """Retrieve hourly bars from the local SQLite cache."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Sub-string date comparison is safe for YYYY-MM-DD HH:MM:SS format
            cursor.execute(
                "SELECT bar_date, open, high, low, close, volume FROM hourly_bars "
                "WHERE ticker = ? AND bar_date >= ? AND bar_date <= ? "
                "ORDER BY bar_date ASC",
                (ticker.upper(), f"{from_date} 00:00:00", f"{to_date} 23:59:59"),
            )
            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "date": row["bar_date"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to query hourly cache for {ticker}: {e}")
            return []

    def _cache_hourly_bars(self, ticker: str, bars: list[HourlyBar]):
        """Save a list of hourly bars to the SQLite cache."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Bulk insert using executemany for high performance
            cursor.executemany(
                "INSERT OR IGNORE INTO hourly_bars (ticker, bar_date, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (ticker.upper(), bar["date"], bar["open"], bar["high"], bar["low"], bar["close"], bar["volume"])
                    for bar in bars
                ],
            )
            conn.commit()
            conn.close()
            logger.debug(f"Cached {len(bars)} hourly bars for {ticker}")
        except Exception as e:
            logger.error(f"Failed to cache hourly bars for {ticker}: {e}")

    async def get_hourly_history(self, ticker: str, from_date: str, to_date: str) -> list[HourlyBar]:
        """Fetch hourly historical chart/bars for a ticker, using local SQLite cache."""
        # 1. Check local SQLite cache first
        cached = self._get_cached_hourly_bars(ticker, from_date, to_date)
        if cached:
            logger.debug(f"Hourly cache hit for {ticker} from {from_date} to {to_date} ({len(cached)} bars)")
            return cached

        # 2. Fetch from FMP API if not cached
        if not self.api_key:
            logger.warning("FMP_API_KEY not set. Cannot fetch hourly history.")
            return []

        logger.info(f"Hourly cache miss for {ticker} from {from_date} to {to_date}. Fetching from FMP API...")

        # Throttling logic
        from core.config import FINANCIAL_API_THROTTLE_SECONDS

        if FINANCIAL_API_THROTTLE_SECONDS > 0:
            await asyncio.sleep(FINANCIAL_API_THROTTLE_SECONDS)

        for attempt in range(1, MARKET_DATA_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
                    resp = await client.get(
                        f"{self.BASE_URL}/historical-chart/1hour",
                        params={"symbol": ticker.upper(), "from": from_date, "to": to_date, "apikey": self.api_key},
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    if not data or not isinstance(data, list):
                        logger.warning(f"No hourly history returned for {ticker} from FMP.")
                        return []

                    # Map to HourlyBar structures
                    bars = []
                    for entry in data:
                        # Skip entries missing critical fields
                        if not all(k in entry for k in ("date", "open", "high", "low", "close")):
                            continue
                        bars.append(
                            {
                                "date": entry["date"],
                                "open": float(entry["open"]),
                                "high": float(entry["high"]),
                                "low": float(entry["low"]),
                                "close": float(entry["close"]),
                                "volume": int(entry.get("volume", 0)),
                            }
                        )

                    # FMP historical-chart returns reverse chronological order (newest first).
                    # Sort ascending by date for logical time progression.
                    bars.sort(key=lambda x: x["date"])

                    # Save to cache
                    if bars:
                        self._cache_hourly_bars(ticker, bars)

                    return bars

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 402:
                    logger.error(f"FMP API Quota Exceeded (402 Payment Required) for {ticker} hourly history")
                    return []
                logger.error(f"HTTP error fetching hourly history for {ticker}: {e}")
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt}/{MARKET_DATA_RETRIES} failed fetching hourly history for {ticker}: {e}"
                )

            if attempt < MARKET_DATA_RETRIES:
                await asyncio.sleep(2 ** (attempt - 1))

        logger.error(f"All attempts failed fetching hourly history for {ticker} via FMP.")
        return []
