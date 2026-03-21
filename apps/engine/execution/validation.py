"""Main validation service for pre-market trade logic."""

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel

from core.config import (
    MIN_MARKET_CAP_BILLIONS,
    MAX_PRICE_DEVIATION_PCT,
    logger
)
from .market_data import MarketDataManager


class ValidationStatus(Enum):
    PASSED = "PASSED"
    REJECTED_HALLUCINATION = "REJECTED_HALLUCINATION"
    REJECTED_PRICE_DEVIATION = "REJECTED_PRICE_DEVIATION"
    REJECTED_LIQUIDITY = "REJECTED_LIQUIDITY"
    REJECTED_REDUNDANCY = "REJECTED_REDUNDANCY"
    REJECTED_MARKET_CLOSED = "REJECTED_MARKET_CLOSED"
    ERROR_PROVIDER = "ERROR_PROVIDER"


class ValidationResult(BaseModel):
    """Result of a trade validation check."""
    ticker: str
    status: ValidationStatus
    reason: Optional[str] = None
    market_price: Optional[float] = None
    market_cap: Optional[float] = None


async def validate_decision(ticker: str, ai_price: Optional[float]) -> ValidationResult:
    """Validate a single trade decision against market guardrails.
    
    Guardrail A: Ticker Existence
    Guardrail B: Price Banding (Skipped if ai_price is None or 0)
    Guardrail C: Liquidity
    """
    # Defensive check: Reject "N/A" or obviously invalid tickers early
    if not ticker or ticker.upper() in ["N/A", "NONE", "NULL", "UNKNOWN"]:
        return ValidationResult(
            ticker=ticker,
            status=ValidationStatus.REJECTED_HALLUCINATION,
            reason=f"Invalid ticker symbol: '{ticker}'"
        )
    
    # Check for invalid characters (tickers should usually be alphanumeric)
    import re
    if not re.match(r"^[A-Z0-9.\-]+$", ticker.upper()):
        return ValidationResult(
            ticker=ticker,
            status=ValidationStatus.REJECTED_HALLUCINATION,
            reason=f"Ticker '{ticker}' contains invalid characters."
        )

    manager = MarketDataManager()
    
    # Guardrail 0: Market Hours
    if not await manager.is_market_open():
        return ValidationResult(
            ticker=ticker,
            status=ValidationStatus.REJECTED_MARKET_CLOSED,
            reason="Market is currently closed. Trading is only allowed during US market hours (09:30-16:00 ET, Mon-Fri, non-holidays)."
        )

    try:
        data = await manager.get_quote(ticker)
    except Exception as e:
        logger.error(f"Error while validating {ticker}: {e}")
        return ValidationResult(
            ticker=ticker,
            status=ValidationStatus.ERROR_PROVIDER,
            reason=f"Processing error: {str(e)}"
        )

    # Guardrail A: Existence
    if not data or not data.exists:
        return ValidationResult(
            ticker=ticker,
            status=ValidationStatus.REJECTED_HALLUCINATION,
            reason=f"Ticker '{ticker}' not found in market data cache or providers."
        )

    # Guardrail B: Price Banding
    # Reject if deviation is > MAX_PRICE_DEVIATION_PCT
    # ONLY if ai_price is provided and > 0.
    if ai_price and ai_price > 0:
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
    # Special Case: Some providers (like IBKR Proxy) don't return market cap for ETFs, 
    # resulting in 0. We allow 0 to pass to avoid blocking liquid ETFs,
    # but still enforce the minimum for stocks where a positive market cap is reported.
    market_cap_billions = data.market_cap / 1_000_000_000
    if 0 < market_cap_billions < MIN_MARKET_CAP_BILLIONS:
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


async def validate_semantic_overlap(ticker: str, reasoning: str, threshold: float = 0.90) -> Optional[str]:
    """Checks if this trade is redundant based on recent similar reasoning.
    
    Returns:
        The reason/ID of the overlapping trade if found, else None.
    """
    if not reasoning:
        return None
        
    from memory.store import find_similar_decision
    
    similar = find_similar_decision(
        ticker=ticker,
        content=reasoning,
        threshold=threshold,
        hours=24 # Look back 24 hours
    )
    
    if similar:
        return f"Semantic overlap with recent trade (ID: {similar['id']}). Reason: {similar['reasoning'][:100]}..."
        
    return None
