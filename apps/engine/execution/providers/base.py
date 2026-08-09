"""Base interface for financial data providers."""

from abc import ABC, abstractmethod
from typing import TypedDict

from pydantic import BaseModel


class TickerData(BaseModel):
    """Normalized data structure for ticker validation."""

    ticker: str
    price: float
    market_cap: float
    exists: bool = True
    currency: str = "USD"
    exchange: str | None = None


class HistoryData(TypedDict, total=False):
    """Historical price entry with volume data."""

    price: float
    open: float
    high: float
    low: float
    volume: int | None
    fetched_at: str


class HourlyBar(TypedDict):
    """Hourly historical price bar."""

    date: str  # Format: "YYYY-MM-DD HH:MM:SS"
    open: float
    high: float
    low: float
    close: float
    volume: int


class FinancialProvider(ABC):
    """Abstract base class for financial API providers."""

    provider_name: str = "base"

    @abstractmethod
    async def get_ticker_data(self, ticker: str) -> TickerData | None:
        """Fetch real-time/delayed ticker data including price and market cap.

        Returns:
            TickerData if found, None if ticker does not exist or error occurs.
        """
        pass

    async def get_ticker_data_batch(self, tickers: list[str]) -> dict[str, TickerData]:
        """Fetch real-time/delayed ticker data for multiple symbols.

        Default implementation just loops through individual calls.
        Override in subclasses to use provider-specific batch endpoints.

        Returns:
            Dict mapping ticker symbol to TickerData.
        """
        results = {}
        for ticker in tickers:
            data = await self.get_ticker_data(ticker)
            if data:
                results[ticker] = data
        return results

    @abstractmethod
    async def get_history(self, ticker: str, days: int = 14) -> list[HistoryData]:
        """Fetch historical price data for a ticker.

        Returns:
            List of HistoryData dicts with 'price', 'volume', and 'fetched_at' (ISO timestamp).
        """
        pass

    async def get_hourly_history(self, ticker: str, from_date: str, to_date: str) -> list[HourlyBar]:
        """Fetch hourly historical chart/bars for a ticker.

        Returns:
            List of HourlyBar dicts containing date, open, high, low, close, volume.
        """
        return []

    async def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 1) -> list[dict]:
        """Fetch fundamental financial key metrics for a ticker.

        Returns:
            List of dicts containing key metrics.
        """
        return []

    async def get_earnings_history(self, ticker: str, limit: int = 8) -> list[dict]:
        """Fetch historical earnings estimates vs actuals and upcoming date.

        Returns:
            List of dicts containing earnings details.
        """
        return []

    @classmethod
    async def disconnect_all(cls):
        """Optional hook to close persistent connections."""
        return
