"""Unit tests for the Pre-Market Validation logic (Approach 3: no AI price)."""

from unittest.mock import AsyncMock, patch

import pytest

from execution.providers.base import TickerData
from execution.validation import ValidationStatus, validate_decision


@pytest.mark.asyncio
async def test_validate_decision_pass():
    """Test that a valid ticker with liquidity passes."""
    mock_data = TickerData(
        ticker="AAPL",
        price=150.0,
        market_cap=2_500_000_000_000.0,  # $2.5T
        exists=True,
    )

    with patch("execution.validation.MarketDataManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(return_value=mock_data)
        mock_manager.is_market_open = AsyncMock(return_value=True)

        result = await validate_decision("AAPL")

        assert result.status == ValidationStatus.PASSED
        assert result.ticker == "AAPL"


@pytest.mark.asyncio
async def test_validate_decision_hallucination():
    """Test that a non-existent ticker is rejected."""
    with patch("execution.validation.MarketDataManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(return_value=None)
        mock_manager.is_market_open = AsyncMock(return_value=True)

        result = await validate_decision("FAKE")

        assert result.status == ValidationStatus.REJECTED_HALLUCINATION
        assert "not found" in result.reason.lower()


@pytest.mark.asyncio
async def test_validate_decision_liquidity():
    """Test that low market cap is rejected (penny stocks)."""
    mock_data = TickerData(
        ticker="PENY",
        price=1.0,
        market_cap=500_000_000.0,  # $500M < $2B
        exists=True,
    )

    with patch("execution.validation.MarketDataManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(return_value=mock_data)
        mock_manager.is_market_open = AsyncMock(return_value=True)

        result = await validate_decision("PENY")

        assert result.status == ValidationStatus.REJECTED_LIQUIDITY
        assert "Insufficient liquidity" in result.reason
