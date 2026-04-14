"""Shared pytest fixtures for main.py tests."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest


@pytest.fixture
def fully_mocked_main():
    """Complete mocking for main.py dependencies.
    
    This fixture provides comprehensive mocking of all external dependencies
    to ensure unit tests are fully isolated and don't hit real DBs, APIs,
    or other external services.
    
    Usage:
        async def test_something(fully_mocked_main):
            md = fully_mocked_main
            # All dependencies are mocked and ready to use
    """
    with patch("main.get_supabase_client") as mock_db, \
         patch("main._stage_dust_cleanup", new_callable=AsyncMock) as mock_dust, \
         patch("main.ingest_newsletters", new_callable=AsyncMock) as mock_ingest, \
         patch("main.upsert_newsletter_snapshot") as mock_upsert, \
         patch("main.Portfolio") as MockPortfolio, \
         patch("execution.market_data.MarketDataManager") as MockMDM, \
         patch("core.utils.MarketDataManager") as MockMDMUtils, \
         patch("main.logger") as mock_logger:
        
        # Setup Portfolio mock
        mock_portfolio_instance = MagicMock()
        MockPortfolio.return_value = mock_portfolio_instance
        mock_portfolio_instance.positions = {}
        mock_portfolio_instance.initialize = AsyncMock()
        mock_portfolio_instance.metrics = MagicMock(total_equity=10000, buying_power=8000, sma=10000)
        mock_portfolio_instance._check_and_sell_dust_positions = AsyncMock()
        mock_portfolio_instance.calculate_reg_t_metrics = MagicMock()
        mock_portfolio_instance.save_metrics = AsyncMock()
        mock_portfolio_instance.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000 cash")
        
        # Setup MarketDataManager mock (used by main.py)
        mock_mdm_instance = MagicMock()
        MockMDM.return_value = mock_mdm_instance
        mock_mdm_instance.get_quote = AsyncMock(return_value=MagicMock(price=100.0, exists=True))
        mock_mdm_instance.get_quotes = AsyncMock(return_value={})
        mock_mdm_instance.get_history = AsyncMock(return_value=[])
        mock_mdm_instance.is_market_open = AsyncMock(return_value=True)
        
        # Setup MarketDataManager mock for core.utils (used by is_market_open_with_logging)
        mock_mdm_utils_instance = MagicMock()
        MockMDMUtils.return_value = mock_mdm_utils_instance
        mock_mdm_utils_instance.is_market_open = AsyncMock(return_value=True)
        
        yield {
            "db": mock_db,
            "dust_cleanup": mock_dust,
            "ingest": mock_ingest,
            "upsert": mock_upsert,
            "portfolio_cls": MockPortfolio,
            "portfolio": mock_portfolio_instance,
            "mdm_cls": MockMDM,
            "mdm": mock_mdm_instance,
            "mdm_utils": mock_mdm_utils_instance,
            "logger": mock_logger
        }
