import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from execution.providers.base import TickerData
from execution.validation import ValidationStatus, validate_decision


@pytest.mark.asyncio
async def test_etf_liquidity_fix():
    """Verify that ETFs with 0 market cap (like from IBKR Proxy) are PASSED."""
    
    # Mock MarketDataManager.get_quote to return a 0 market cap TickerData (simulating ETF in Proxy)
    mock_data = TickerData(
        ticker="XLE",
        price=55.44,
        market_cap=0.0,
        exists=True
    )
    
    with patch("execution.validation.MarketDataManager") as MockManager:
        instance = MockManager.return_value
        instance.get_quote = AsyncMock(return_value=mock_data)
        instance.is_market_open = AsyncMock(return_value=True)
        
        # Test ETF with 0 market cap (should PASS now)
        result = await validate_decision("XLE")
        assert result.status == ValidationStatus.PASSED
        assert result.ticker == "XLE"

@pytest.mark.asyncio
async def test_small_cap_rejection_still_works():
    """Verify that actual small-cap stocks are still REJECTED if they have a positive market cap below threshold."""
    
    # Mock MarketDataManager.get_quote to return a small but positive market cap (e.g., $100M)
    mock_data = TickerData(
        ticker="SMALL",
        price=10.0,
        market_cap=100_000_000.0, # $0.1B
        exists=True
    )
    
    with patch("execution.validation.MarketDataManager") as MockManager:
        instance = MockManager.return_value
        instance.get_quote = AsyncMock(return_value=mock_data)
        instance.is_market_open = AsyncMock(return_value=True)
        
        # Test small cap with $0.1B (should be REJECTED, threshold is $2B)
        result = await validate_decision("SMALL")
        assert result.status == ValidationStatus.REJECTED_LIQUIDITY
        assert "Insufficient liquidity" in result.reason

if __name__ == "__main__":
    # Setup for manual run
    async def run_tests():
        print("Running ETF Liquidity Fix Test...")
        try:
            await test_etf_liquidity_fix()
            print("✅ test_etf_liquidity_fix PASSED")
        except Exception as e:
            print(f"❌ test_etf_liquidity_fix FAILED: {e}")
            
        print("\nRunning Small Cap Rejection Test...")
        try:
            await test_small_cap_rejection_still_works()
            print("✅ test_small_cap_rejection_still_works PASSED")
        except Exception as e:
            print(f"❌ test_small_cap_rejection_still_works FAILED: {e}")

    # CoroutineMock polyfill removed

    asyncio.run(run_tests())
