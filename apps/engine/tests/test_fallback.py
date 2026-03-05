import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from execution.market_data import MarketDataManager
from execution.providers.proxy_ibkr import ProxyIBKRProvider
from execution.providers.base import TickerData, FinancialProvider

class FakeYFinanceProvider(FinancialProvider):
    provider_name = "yfinance"
    async def get_ticker_data(self, ticker: str):
        return TickerData(ticker=ticker, price=180.0, market_cap=3000000000000.0, exists=True)
    async def get_history(self, ticker: str, days: int):
        return [{"price": 100.0, "fetched_at": "now"}]

@pytest.mark.asyncio
async def test_manager_fallback_to_yfinance():
    """Verify that MarketDataManager falls back to YFinance when primary provider returns None."""
    with patch("execution.market_data.get_financial_provider", return_value=ProxyIBKRProvider()):
        with patch("execution.market_data.get_supabase_client"):
            manager = MarketDataManager()
            
            # Mock Proxy provider to fail
            mock_proxy = AsyncMock(spec=ProxyIBKRProvider)
            mock_proxy.get_ticker_data.return_value = None
            manager.provider = mock_proxy
            
            # Use FakeYFinanceProvider
            with patch("execution.providers.yfinance.YFinanceProvider", new=FakeYFinanceProvider):
                # Mock cache and history checks to speed up
                manager._get_from_cache = MagicMock(return_value=None)
                manager._save_to_cache = MagicMock()
                
                data = await manager.get_quote("AAPL")
                
                assert data is not None
                assert data.price == 180.0
                assert mock_proxy.get_ticker_data.called

@pytest.mark.asyncio
async def test_manager_history_fallback():
    """Verify history fallback at manager level."""
    with patch("execution.market_data.get_financial_provider", return_value=ProxyIBKRProvider()):
        with patch("execution.market_data.get_supabase_client"):
            manager = MarketDataManager()
            
            # Mock Primary failure
            mock_proxy = AsyncMock(spec=ProxyIBKRProvider)
            mock_proxy.get_history.return_value = []
            manager.provider = mock_proxy
            
            print("About to call get_history")
            with patch("execution.providers.yfinance.YFinanceProvider", new=FakeYFinanceProvider):
                # Mock DB check
                manager.client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
                
                history = await manager.get_history("AAPL", days=1)
                
                assert len(history) == 1
                assert history[0]["price"] == 100.0
                assert mock_proxy.get_history.called
