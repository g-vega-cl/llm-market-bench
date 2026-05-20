"""Factory for financial data providers."""

from core.config import FINANCIAL_PROVIDER, logger

from .base import FinancialProvider
from .fmp import FMPProvider
from .yfinance import YFinanceProvider


def get_financial_provider(provider_name: str = None) -> FinancialProvider:
    """Factory to return a financial provider instance.

    If provider_name is not provided, it defaults to the configured FINANCIAL_PROVIDER.
    """
    target = provider_name or FINANCIAL_PROVIDER

    if target == "fmp":
        return FMPProvider()
    elif target == "yfinance":
        return YFinanceProvider()

    # Default/Fallback
    logger.warning(f"Unknown financial provider '{target}'. Defaulting to fmp.")
    return FMPProvider()


def get_active_provider_class():
    """Returns the class of the currently configured provider."""
    _provider_map = {
        "fmp": FMPProvider,
        "yfinance": YFinanceProvider,
    }
    return _provider_map.get(FINANCIAL_PROVIDER, FMPProvider)
