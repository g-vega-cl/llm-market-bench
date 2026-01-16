"""Factory for financial data providers."""

from core.config import FINANCIAL_PROVIDER, logger
from .base import FinancialProvider
from .fmp import FMPProvider
from .yfinance import YFinanceProvider

def get_financial_provider() -> FinancialProvider:
    """Factory to return the configured financial provider."""
    if FINANCIAL_PROVIDER == "fmp":
        return FMPProvider()
    elif FINANCIAL_PROVIDER == "yfinance":
        return YFinanceProvider()
    
    # Default/Fallback
    logger.warning(f"Unknown financial provider '{FINANCIAL_PROVIDER}'. Defaulting to yfinance.")
    return YFinanceProvider()
