"""Main validation service for pre-market trade logic."""

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel

from core.config import (
    FINANCIAL_PROVIDER,
    MIN_MARKET_CAP_BILLIONS,
    MAX_PRICE_DEVIATION_PCT,
    logger
)
from .providers.base import FinancialProvider, TickerData
from .providers.fmp import FMPProvider


class ValidationStatus(Enum):
    PASSED = "PASSED"
    REJECTED_HALLUCINATION = "REJECTED_HALLUCINATION"
    REJECTED_PRICE_DEVIATION = "REJECTED_PRICE_DEVIATION"
    REJECTED_LIQUIDITY = "REJECTED_LIQUIDITY"
    ERROR_PROVIDER = "ERROR_PROVIDER"


class ValidationResult(BaseModel):
    """Result of a trade validation check."""
    ticker: str
    status: ValidationStatus
    reason: Optional[str] = None
    market_price: Optional[float] = None
    market_cap: Optional[float] = None


def get_financial_provider() -> FinancialProvider:
    """Factory to return the configured financial provider."""
    if FINANCIAL_PROVIDER == "fmp":
        return FMPProvider()
    
    # Default/Fallback
    logger.warning(f"Unknown financial provider '{FINANCIAL_PROVIDER}'. Defaulting to FMP.")
    return FMPProvider()


async def validate_decision(ticker: str, ai_price: float) -> ValidationResult:
    """Validate a single trade decision against market guardrails.
    
    Guardrail A: Ticker Existence
    Guardrail B: Price Banding
    Guardrail C: Liquidity
    """
    provider = get_financial_provider()
    
    try:
        data = await provider.get_ticker_data(ticker)
    except Exception as e:
        logger.error(f"Provider error while validating {ticker}: {e}")
        return ValidationResult(
            ticker=ticker,
            status=ValidationStatus.ERROR_PROVIDER,
            reason=f"Provider error: {str(e)}"
        )

    # Guardrail A: Existence
    if not data or not data.exists:
        return ValidationResult(
            ticker=ticker,
            status=ValidationStatus.REJECTED_HALLUCINATION,
            reason=f"Ticker '{ticker}' not found in market data."
        )

    # Guardrail B: Price Banding
    # Reject if deviation is > MAX_PRICE_DEVIATION_PCT
    price_diff = abs(ai_price - data.price)
    deviation_pct = (price_diff / data.price) * 100 if data.price > 0 else 0
    
    if deviation_pct > MAX_PRICE_DEVIATION_PCT:
        return ValidationResult(
            ticker=ticker,
            status=ValidationStatus.REJECTED_PRICE_DEVIATION,
            reason=f"Price deviation too high: {deviation_pct:.1f}% (AI: ${ai_price}, Market: ${data.price})",
            market_price=data.price,
            market_cap=data.market_cap
        )

    # Guardrail C: Liquidity (Market Cap)
    market_cap_billions = data.market_cap / 1_000_000_000
    if market_cap_billions < MIN_MARKET_CAP_BILLIONS:
        return ValidationResult(
            ticker=ticker,
            status=ValidationStatus.REJECTED_LIQUIDITY,
            reason=f"Insufficient liquidity: Market Cap ${market_cap_billions:.2f}B < ${MIN_MARKET_CAP_BILLIONS}B",
            market_price=data.price,
            market_cap=data.market_cap
        )

    return ValidationResult(
        ticker=ticker,
        status=ValidationStatus.PASSED,
        market_price=data.price,
        market_cap=data.market_cap
    )
