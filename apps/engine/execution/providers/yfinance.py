"""yfinance implementation of FinancialProvider."""

import asyncio
import time
import yfinance as yf
from typing import Optional
from .base import FinancialProvider, TickerData
from core.config import logger


class YFinanceProvider(FinancialProvider):
    """Provider for Yahoo Finance API via yfinance library."""

    _last_call_time = 0.0  # Shared across all instances to throttle globally

    async def get_ticker_data(self, ticker: str) -> Optional[TickerData]:
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

            if not info or "symbol" not in info:
                # yfinance often returns an almost empty dict if ticker is not found
                # or it might throw an error. Checking for 'symbol' is a good proxy.
                if not info or info.get('trailingPegRatio') is None and info.get('marketCap') is None:
                    logger.warning(f"Ticker {ticker} not found on yfinance or has no data.")
                    return None

            # Different keys might contain price depending on market state
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            market_cap = info.get("marketCap", 0)

            if price is None:
                logger.warning(f"Could not find price for {ticker} on yfinance.")
                return None

            return TickerData(
                ticker=ticker,
                price=float(price),
                market_cap=float(market_cap),
                exists=True,
                currency=info.get("currency", "USD"),
                exchange=info.get("exchange")
            )

        except Exception as e:
            logger.error(f"Unexpected error fetching data from yfinance for {ticker}: {e}")
            return None
