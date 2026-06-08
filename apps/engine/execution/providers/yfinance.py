"""yfinance implementation of FinancialProvider."""

import asyncio
import logging
import time

import yfinance as yf

from .base import FinancialProvider, TickerData

logger = logging.getLogger("engine.execution.providers.yfinance")


class YFinanceProvider(FinancialProvider):
    """Provider for Yahoo Finance API via yfinance library."""

    provider_name = "yfinance"

    _last_call_time = 0.0  # Shared across all instances to throttle globally

    async def get_ticker_data(self, ticker: str) -> TickerData | None:
        # Throttling logic
        from core.config import FINANCIAL_API_THROTTLE_SECONDS

        if FINANCIAL_API_THROTTLE_SECONDS > 0:
            elapsed = time.time() - YFinanceProvider._last_call_time
            wait_time = FINANCIAL_API_THROTTLE_SECONDS - elapsed
            if wait_time > 0:
                logger.debug(f"Throttling yfinance call for {ticker}: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

        # Update last call time just before the request
        YFinanceProvider._last_call_time = time.time()

        try:
            # yfinance is synchronous, so we run it in a thread to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            t = await loop.run_in_executor(None, lambda: yf.Ticker(ticker))
            info = await loop.run_in_executor(None, lambda: t.info)

            if not info or (
                "symbol" not in info and info.get("trailingPegRatio") is None and info.get("marketCap") is None
            ):
                logger.warning(f"Ticker {ticker} not found on yfinance or has no data.")
                return None

            # Different keys might contain price depending on market state
            price = info.get("currentPrice")
            if price is None:
                price = info.get("regularMarketPrice")
                if price is not None:
                    logger.warning(
                        f"currentPrice missing for {ticker} on yfinance. Falling back to regularMarketPrice."
                    )
                else:
                    price = info.get("previousClose")
                    if price is not None:
                        logger.warning(
                            f"currentPrice and regularMarketPrice missing for {ticker} on yfinance. "
                            f"Falling back to previousClose."
                        )

            # Market Cap fallback for ETFs: yfinance often puts ETF size in totalAssets or netAssets
            market_cap = info.get("marketCap")
            if market_cap is None:
                market_cap = info.get("totalAssets")
                if market_cap is not None:
                    logger.warning(f"marketCap missing for {ticker} on yfinance. Falling back to totalAssets.")
                else:
                    market_cap = info.get("netAssets")
                    if market_cap is not None:
                        logger.warning(
                            f"marketCap and totalAssets missing for {ticker} on yfinance. Falling back to netAssets."
                        )
                    else:
                        market_cap = 0

            if price is None:
                logger.warning(f"Could not find price for {ticker} on yfinance.")
                return None

            return TickerData(
                ticker=ticker,
                price=float(price),
                market_cap=float(market_cap),
                exists=True,
                currency=info.get("currency", "USD"),
                exchange=info.get("exchange"),
            )

        except Exception:
            logger.exception(f"Unexpected error fetching data from yfinance for {ticker}")
            return None

    async def get_history(self, ticker: str, days: int = 14) -> list[dict]:
        """Fetch historical price data using yfinance."""
        try:
            loop = asyncio.get_event_loop()
            t = await loop.run_in_executor(None, lambda: yf.Ticker(ticker))
            # period parameter can be 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            # For specific days, we can use period="1mo" or similar if days <= 30
            # For exact days, period doesn't work well, but range does.
            # Let's use a safe period like '1mo' for up to 30 days.
            period = "1mo" if days <= 30 else "3mo"
            hist = await loop.run_in_executor(None, lambda: t.history(period=period))

            if hist.empty:
                logger.warning(f"No history found for {ticker} on yfinance.")
                return []

            # Take the last N days
            recent = hist.tail(days)
            results = []
            for timestamp, row in recent.iterrows():
                results.append({"price": float(row["Close"]), "fetched_at": timestamp.isoformat()})

            # YFinance returns in ascending order (oldest first).
            # Our engine usually expects descending (latest first) or we handle it in tools.
            # Let's keep it latest first for consistency with Supabase queries.
            results.reverse()
            return results

        except Exception:
            logger.exception(f"Error fetching history from yfinance for {ticker}")
            return []

    async def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 1) -> list[dict]:
        """Fetch fundamental financial key metrics for a ticker from yfinance."""
        try:
            loop = asyncio.get_event_loop()
            t = await loop.run_in_executor(None, lambda: yf.Ticker(ticker))
            info = await loop.run_in_executor(None, lambda: t.info)

            if not info:
                logger.warning(f"No key metrics found for {ticker} on yfinance.")
                return []

            # Map yfinance info to FMP schema
            fcf = info.get("freeCashflow")
            market_cap = info.get("marketCap") or info.get("totalAssets") or info.get("netAssets") or 0
            fcf_yield = None
            if fcf and market_cap:
                fcf_yield = float(fcf) / float(market_cap)

            debt_to_equity = info.get("debtToEquity")
            if debt_to_equity is not None:
                # yfinance returns debtToEquity in percent (e.g., 210.0 for 2.1)
                debt_to_equity = float(debt_to_equity) / 100.0

            # Determine fiscal year/date
            import datetime

            fiscal_year_end = info.get("lastFiscalYearEnd")
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            calendar_year = str(datetime.datetime.now().year)
            if fiscal_year_end:
                try:
                    # fiscal_year_end is epoch seconds
                    dt = datetime.datetime.fromtimestamp(fiscal_year_end)
                    date_str = dt.strftime("%Y-%m-%d")
                    calendar_year = str(dt.year)
                except Exception:
                    pass

            metric = {
                "symbol": ticker.upper(),
                "date": date_str,
                "calendarYear": calendar_year,
                "period": "TTM",
                "peRatio": info.get("trailingPE"),
                "priceToSalesRatio": info.get("priceToSalesTrailing12Months"),
                "pbRatio": info.get("priceToBook"),
                "enterpriseValueOverEBITDA": info.get("enterpriseToEbitda"),
                "debtToEquity": debt_to_equity,
                "currentRatio": info.get("currentRatio"),
                "roe": info.get("returnOnEquity"),
                "dividendYield": info.get("dividendYield"),
                "freeCashFlowYield": fcf_yield,
                "bookValuePerShare": info.get("bookValue"),
                "revenuePerShare": info.get("revenuePerShare"),
            }

            # Filter out None values to keep it clean, but keep keys
            metric = {k: v for k, v in metric.items() if v is not None}
            return [metric]
        except Exception:
            logger.exception(f"Error fetching key metrics from yfinance for {ticker}")
            return []
