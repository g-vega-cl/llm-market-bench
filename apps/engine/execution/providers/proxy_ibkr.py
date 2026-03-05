import httpx
import logging
from typing import Optional, List, Dict
from .base import FinancialProvider, TickerData
from core.config import IBKR_PROXY_URL, IBKR_PROXY_TOKEN, logger

class ProxyIBKRProvider(FinancialProvider):
    """Provider that fetches IBKR data via a secure Proxy API."""
    provider_name = "ibkr_proxy"

    def __init__(self):
        if not IBKR_PROXY_URL:
            logger.warning("IBKR_PROXY_URL not set. ProxyIBKRProvider will fail.")
        self.base_url = IBKR_PROXY_URL.rstrip("/") if IBKR_PROXY_URL else ""
        self.headers = {
            "Authorization": f"Bearer {IBKR_PROXY_TOKEN}" if IBKR_PROXY_TOKEN else ""
        }

    async def get_ticker_data(self, ticker: str) -> Optional[TickerData]:
        """Fetch ticker data from the proxy."""
        if not self.base_url:
            return None
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/price/{ticker}",
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return TickerData(**data)
                else:
                    logger.warning(f"Proxy error for {ticker}: {response.status_code}")
                    return None
            except Exception as e:
                logger.error(f"Failed to fetch {ticker} from proxy: {e}")
                return None

    async def get_history(self, ticker: str, days: int = 14) -> List[Dict]:
        """Fetch historical data from the proxy."""
        if not self.base_url:
            return []

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/history/{ticker}?days={days}",
                    headers=self.headers,
                    timeout=15.0
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Proxy history error for {ticker}: {response.status_code}")
                    return []
            except Exception as e:
                logger.error(f"Failed to fetch history for {ticker} from proxy: {e}")
                return []
