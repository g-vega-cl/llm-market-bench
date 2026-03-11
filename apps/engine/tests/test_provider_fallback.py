import asyncio
import pytest
from unittest.mock import MagicMock, patch
from execution.market_data import MarketDataManager
from execution.providers.base import TickerData

@pytest.mark.asyncio
async def test_fallback_to_last_known():
    """Verify that MarketDataManager falls back to last known price when providers fail."""
    
    ticker = "FAILED_TICKER"
    
    # 1. Mock _get_from_cache to return None (cache miss)
    # 2. Mock _fetch_with_backoff to return None (primary and fallback fail)
    # 3. Mock _get_last_known_price to return a value
    
    with patch.object(MarketDataManager, '_get_from_cache', return_value=None), \
         patch.object(MarketDataManager, '_fetch_with_backoff', return_value=None), \
         patch.object(MarketDataManager, '_get_last_known_price') as mock_history:
        
        mock_history.return_value = TickerData(
            ticker=ticker,
            price=123.45,
            market_cap=1000000000,
            exists=True
        )
        
        manager = MarketDataManager()
        result = await manager.get_quote(ticker)
        
        assert result is not None
        assert result.price == 123.45
        assert result.ticker == ticker
        print(f"✅ Fallback to last known price works for {ticker}")

@pytest.mark.asyncio
async def test_fatal_failure_when_no_history():
    """Verify that MarketDataManager returns None and logs error when everything fails."""
    
    ticker = "TOTALLY_FAILED"
    
    with patch.object(MarketDataManager, '_get_from_cache', return_value=None), \
         patch.object(MarketDataManager, '_fetch_with_backoff', return_value=None), \
         patch.object(MarketDataManager, '_get_last_known_price', return_value=None):
        
        manager = MarketDataManager()
        result = await manager.get_quote(ticker)
        
        assert result is None
        print(f"✅ Fatal failure handling works for {ticker}")

if __name__ == "__main__":
    async def run_tests():
        print("Running Provider Fallback Tests...")
        try:
            await test_fallback_to_last_known()
        except Exception as e:
            print(f"❌ test_fallback_to_last_known FAILED: {e}")
            
        try:
            await test_fatal_failure_when_no_history()
        except Exception as e:
            print(f"❌ test_fatal_failure_when_no_history FAILED: {e}")

    # Add CoroutineMock if not available
    if not hasattr(patch, "CoroutineMock"):
        class CoroutineMock(MagicMock):
            async def __call__(self, *args, **kwargs):
                return super(CoroutineMock, self).__call__(*args, **kwargs)
        asyncio.CoroutineMock = CoroutineMock

    asyncio.run(run_tests())
