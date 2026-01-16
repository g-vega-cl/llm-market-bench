"""Unit tests for the Pre-Market Validation logic."""

import pytest
from unittest.mock import AsyncMock, patch
from execution.validation import validate_decision, ValidationStatus
from execution.providers.base import TickerData


@pytest.mark.asyncio
async def test_validate_decision_pass():
    """Test that a valid ticker with correct price and liquidity passes."""
    mock_data = TickerData(
        ticker="AAPL",
        price=150.0,
        market_cap=2_500_000_000_000.0,  # $2.5T
        exists=True
    )
    
    with patch("execution.validation.MarketDataManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(return_value=mock_data)
        
        # AI suggests $155 (within 15% of $150)
        result = await validate_decision("AAPL", 155.0)
        
        assert result.status == ValidationStatus.PASSED
        assert result.ticker == "AAPL"


@pytest.mark.asyncio
async def test_validate_decision_hallucination():
    """Test that a non-existent ticker is rejected."""
    with patch("execution.validation.MarketDataManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(return_value=None)
        
        result = await validate_decision("FAKE", 100.0)
        
        assert result.status == ValidationStatus.REJECTED_HALLUCINATION
        assert "not found" in result.reason.lower()


@pytest.mark.asyncio
async def test_validate_decision_price_deviation():
    """Test that high price deviation is rejected."""
    mock_data = TickerData(
        ticker="TSLA",
        price=200.0,
        market_cap=600_000_000_000.0,
        exists=True
    )
    
    with patch("execution.validation.MarketDataManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(return_value=mock_data)
        
        # AI suggests $50 (deviation > 15%)
        result = await validate_decision("TSLA", 50.0)
        
        assert result.status == ValidationStatus.REJECTED_PRICE_DEVIATION
        assert "Price deviation too high" in result.reason


@pytest.mark.asyncio
async def test_validate_decision_liquidity():
    """Test that low market cap is rejected (penny stocks)."""
    mock_data = TickerData(
        ticker="PENY",
        price=1.0,
        market_cap=500_000_000.0,  # $500M < $2B
        exists=True
    )
    
    with patch("execution.validation.MarketDataManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(return_value=mock_data)
        
        result = await validate_decision("PENY", 1.0)
        
        assert result.status == ValidationStatus.REJECTED_LIQUIDITY
        assert "Insufficient liquidity" in result.reason


@pytest.mark.asyncio
async def test_validate_decision_no_ai_price():
    """Test that validating without an AI price skips banding but checks liquidity."""
    mock_data = TickerData(
        ticker="MSFT",
        price=400.0,
        market_cap=3_000_000_000_000.0,
        exists=True
    )
    
    with patch("execution.validation.MarketDataManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(return_value=mock_data)
        
        # ai_price is None
        result = await validate_decision("MSFT", None)
        
        assert result.status == ValidationStatus.PASSED
        assert result.ticker == "MSFT"
        assert result.market_price == 400.0
