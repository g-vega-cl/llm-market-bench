"""Factory for financial data providers."""

from core.config import FINANCIAL_PROVIDER, FALLBACK_FINANCIAL_PROVIDER, logger
from .base import FinancialProvider
from .fmp import FMPProvider
from .yfinance import YFinanceProvider
from .ibkr import IBKRProvider
from .proxy_ibkr import ProxyIBKRProvider

def get_financial_provider(provider_name: str = None) -> FinancialProvider:
    """Factory to return a financial provider instance.
    
    If provider_name is not provided, it defaults to the configured FINANCIAL_PROVIDER.
    """
    target = provider_name or FINANCIAL_PROVIDER
    
    if target == "fmp":
        return FMPProvider()
    elif target == "yfinance":
        return YFinanceProvider()
    elif target == "ibkr":
        logger.info("Using legacy IBKR provider.")
        return IBKRProvider()
    elif target == "ibkr_proxy":
        logger.info("Using IBKR Proxy provider.")
        return ProxyIBKRProvider()
    
    # Default/Fallback
    logger.warning(f"Unknown financial provider '{target}'. Defaulting to yfinance.")
    return YFinanceProvider()

def get_active_provider_class():
    """Returns the class of the currently configured provider."""
    if FINANCIAL_PROVIDER == "fmp":
        return FMPProvider
    elif FINANCIAL_PROVIDER == "yfinance":
        return YFinanceProvider
    elif FINANCIAL_PROVIDER == "ibkr":
        return IBKRProvider
    elif FINANCIAL_PROVIDER == "ibkr_proxy":
        return ProxyIBKRProvider
    return YFinanceProvider
