"""Base interface for financial data providers."""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class TickerData(BaseModel):
    """Normalized data structure for ticker validation."""

    ticker: str
    price: float
    market_cap: float
    exists: bool = True
    currency: str = "USD"
    exchange: str | None = None


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
    async def get_history(self, ticker: str, days: int = 14) -> list[dict]:
        """Fetch historical price data for a ticker.

        Returns:
            List of dicts with 'price' and 'fetched_at' (ISO timestamp).
        """
        pass

    @classmethod
    async def disconnect_all(cls):
        """Optional hook to close persistent connections."""
        return
