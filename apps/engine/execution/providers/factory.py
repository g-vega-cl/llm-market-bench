"""Factory for financial data providers."""

from core.config import FINANCIAL_PROVIDER, logger
from .base import FinancialProvider
from .fmp import FMPProvider
from .yfinance import YFinanceProvider
from .ibkr import IBKRProvider
from .proxy_ibkr import ProxyIBKRProvider

def get_financial_provider() -> FinancialProvider:
    """Factory to return the configured financial provider."""
    if FINANCIAL_PROVIDER == "fmp":
        return FMPProvider()
    elif FINANCIAL_PROVIDER == "yfinance":
        return YFinanceProvider()
    elif FINANCIAL_PROVIDER == "ibkr":
        # Note: IBKR is kept as a legacy provider. 
        # It requires a running TWS/Gateway instance.
        logger.info("Using legacy IBKR provider.")
        return IBKRProvider()
    elif FINANCIAL_PROVIDER == "ibkr_proxy":
        logger.info("Using IBKR Proxy provider.")
        return ProxyIBKRProvider()
    
    # Default/Fallback
    logger.warning(f"Unknown financial provider '{FINANCIAL_PROVIDER}'. Defaulting to yfinance.")
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
