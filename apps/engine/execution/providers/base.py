"""Base interface for financial data providers."""

from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional


class TickerData(BaseModel):
    """Normalized data structure for ticker validation."""
    ticker: str
    price: float
    market_cap: float
    exists: bool = True
    currency: str = "USD"
    exchange: Optional[str] = None


class FinancialProvider(ABC):
    """Abstract base class for financial API providers."""

    @abstractmethod
    async def get_ticker_data(self, ticker: str) -> Optional[TickerData]:
        """Fetch real-time/delayed ticker data including price and market cap.
        
        Returns:
            TickerData if found, None if ticker does not exist or error occurs.
        """
        pass

    @abstractmethod
    async def get_history(self, ticker: str, days: int = 14) -> list[dict]:
        """Fetch historical price data for a ticker.
        
        Returns:
            List of dicts with 'price' and 'fetched_at' (ISO timestamp).
        """
        pass
