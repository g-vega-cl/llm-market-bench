"""Financial Modeling Prep (FMP) implementation of FinancialProvider."""

import httpx
from typing import Optional
from .base import FinancialProvider, TickerData
from core.config import FINANCIAL_API_KEY, logger


class FMPProvider(FinancialProvider):
    """Provider for Financial Modeling Prep API."""

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self):
        if not FINANCIAL_API_KEY:
            logger.warning("FINANCIAL_API_KEY not found in environment. FMP validation will be disabled.")
        self.api_key = FINANCIAL_API_KEY

    async def get_ticker_data(self, ticker: str) -> Optional[TickerData]:
        if not self.api_key:
            return None

        try:
            async with httpx.AsyncClient() as client:
                # 1. Get Quote (for price and existence)
                quote_resp = await client.get(
                    f"{self.BASE_URL}/quote/{ticker}",
                    params={"apikey": self.api_key}
                )
                quote_resp.raise_for_status()
                quote_data = quote_resp.json()

                if not quote_data:
                    logger.warning(f"Ticker {ticker} not found on FMP.")
                    return None

                # 2. Get Profile (for market cap)
                profile_resp = await client.get(
                    f"{self.BASE_URL}/profile/{ticker}",
                    params={"apikey": self.api_key}
                )
                profile_resp.raise_for_status()
                profile_data = profile_resp.json()

                if not profile_data:
                    logger.warning(f"Could not find profile for {ticker} on FMP.")
                    return None

                q = quote_data[0]
                p = profile_data[0]

                return TickerData(
                    ticker=ticker,
                    price=float(q.get("price", 0)),
                    market_cap=float(p.get("mktCap", 0)),
                    exists=True,
                    currency=q.get("currency", "USD"),
                    exchange=q.get("exchange")
                )

        except Exception as e:
            logger.error(f"Error fetching data from FMP for {ticker}: {e}")
            return None
