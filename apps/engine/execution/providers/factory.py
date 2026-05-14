"""Factory for financial data providers."""

from core.config import FINANCIAL_PROVIDER, logger

from .base import FinancialProvider
from .fmp import FMPProvider
from .ibkr import IBKRProvider
from .proxy_ibkr import ProxyIBKRProvider
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
    elif target == "ibkr":
        logger.info("Using legacy IBKR provider.")
        return IBKRProvider()
    elif target == "ibkr_proxy":
        logger.info("Using IBKR Proxy provider.")
        return ProxyIBKRProvider()
    
    # Default/Fallback
    logger.warning(f"Unknown financial provider '{target}'. Defaulting to fmp.")
    return FMPProvider()

def get_active_provider_class():
    """Returns the class of the currently configured provider."""
    _provider_map = {
        "fmp": FMPProvider,
        "yfinance": YFinanceProvider,
        "ibkr": IBKRProvider,
        "ibkr_proxy": ProxyIBKRProvider,
    }
    return _provider_map.get(FINANCIAL_PROVIDER, FMPProvider)
