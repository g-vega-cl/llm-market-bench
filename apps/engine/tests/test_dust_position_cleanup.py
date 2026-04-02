"""Tests for the 10% minimum position rule (dust position cleanup)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from execution.portfolio import Portfolio


@pytest.fixture
def mock_supabase():
    """Setup mock Supabase client."""
    with patch("execution.portfolio.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock portfolio fetch
        portfolio_query = mock_client.table.return_value.select.return_value.eq.return_value
        portfolio_query.execute.return_value.data = [
            {
                "id": "test-portfolio-id",
                "owner_id": "test-agent",
                "cash_balance": 5000.0,
                "sma": 5000.0,
                "total_equity": 10000.0,
                "buying_power": 20000.0,
                "excess_liquidity": 7000.0,
                "maintenance_margin": 3000.0,
                "realized": 5000.0
            }
        ]
        
        # Mock positions fetch
        positions_query = mock_client.table.return_value.select.return_value.eq.return_value
        positions_query.execute.return_value.data = [
            {"ticker": "AAPL", "quantity": 10, "average_cost_basis": 150.0},
            {"ticker": "XYZ", "quantity": 5, "average_cost_basis": 100.0}
        ]
        
        yield mock_client


@pytest.mark.asyncio
async def test_dust_position_cleanup_after_partial_sell(mock_supabase):
    """Verify that positions below 10% of equity are automatically sold after a SELL trade."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()
    
    # Setup: Portfolio has $10,000 equity, owns AAPL (3 shares @ $150 = $450) and XYZ (5 shares @ $100 = $500)
    # Both are below 10% threshold ($1,000)
    portfolio.positions = {
        "AAPL": MagicMock(ticker="AAPL", quantity=3, average_cost_basis=150.0),  # $450 value (below 10%)
        "XYZ": MagicMock(ticker="XYZ", quantity=5, average_cost_basis=100.0)  # $500 value (below 10%)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"
    
    # Mock market data
    with patch("execution.portfolio.MarketDataManager") as MockMDM:
        mock_mdm = MockMDM.return_value
        mock_mdm.get_quote = AsyncMock()
        mock_mdm.get_quote.side_effect = lambda t: AsyncMock(return_value=MagicMock(price=150.0 if t == "AAPL" else 100.0))()
        
        # Mock DB operations
        mock_supabase.table.return_value.delete.return_value.match.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-123"}])
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        # Simulate current prices
        current_prices = {"AAPL": 150.0, "XYZ": 100.0}
        
        # Run dust cleanup
        await portfolio._check_and_sell_dust_positions(current_prices)
        
        # Verify both dust positions were sold (delete called for each)
        assert mock_supabase.table.return_value.delete.call_count >= 2
        # Verify trades were recorded
        assert mock_supabase.table.return_value.insert.call_count >= 2


@pytest.mark.asyncio
async def test_no_cleanup_for_positions_above_threshold(mock_supabase):
    """Verify that positions above 10% threshold are not sold."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()
    
    # Setup: Portfolio has $10,000 equity, owns large position
    portfolio.positions = {
        "AAPL": MagicMock(ticker="AAPL", quantity=100, average_cost_basis=150.0)  # $15,000 value (above 10%)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"
    
    current_prices = {"AAPL": 150.0}
    
    # Run dust cleanup
    await portfolio._check_and_sell_dust_positions(current_prices)
    
    # Verify no positions were sold
    mock_supabase.table.return_value.delete.assert_not_called()
    mock_supabase.table.return_value.insert.assert_not_called()
    
    # Position should still exist
    assert "AAPL" in portfolio.positions


@pytest.mark.asyncio
async def test_dust_cleanup_with_zero_value_position(mock_supabase):
    """Verify that positions with zero or negative value are ignored."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()
    
    # Setup: Portfolio has a position with zero quantity
    portfolio.positions = {
        "DEAD": MagicMock(ticker="DEAD", quantity=0, average_cost_basis=50.0)  # $0 value
    }
    portfolio.metrics = MagicMock(total_equity=10000.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"
    
    current_prices = {"DEAD": 0.0}
    
    # Run dust cleanup
    await portfolio._check_and_sell_dust_positions(current_prices)
    
    # Verify no action taken for zero-value position
    mock_supabase.table.return_value.delete.assert_not_called()
    mock_supabase.table.return_value.insert.assert_not_called()


@pytest.mark.asyncio
async def test_dust_cleanup_updates_portfolio_metrics(mock_supabase):
    """Verify that dust cleanup properly updates portfolio metrics after selling."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()
    
    # Setup: Small dust position
    portfolio.positions = {
        "DUST": MagicMock(ticker="DUST", quantity=2, average_cost_basis=100.0)  # $200 value (below 10%)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"
    
    current_prices = {"DUST": 100.0}
    
    # Mock DB operations to track calls
    mock_supabase.table.return_value.delete.return_value.match.return_value.execute.return_value = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-456"}])
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    
    # Run dust cleanup
    await portfolio._check_and_sell_dust_positions(current_prices)
    
    # Verify portfolio was updated
    assert mock_supabase.table.return_value.update.called
    # Position should be removed
    assert "DUST" not in portfolio.positions
    # Cash should increase by sale proceeds ($200)
    assert portfolio.cash_balance == 5200.0


@pytest.mark.asyncio
async def test_dust_cleanup_handles_exceptions_gracefully(mock_supabase):
    """Verify that exceptions during dust cleanup are logged but don't crash."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()
    
    # Setup: Position that will cause an error
    portfolio.positions = {
        "ERROR": MagicMock(ticker="ERROR", quantity=5, average_cost_basis=100.0)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"
    
    current_prices = {"ERROR": 100.0}
    
    # Mock DB to raise an exception
    mock_supabase.table.return_value.delete.return_value.match.return_value.execute.side_effect = Exception("DB Error")
    
    # Run dust cleanup - should not crash
    await portfolio._check_and_sell_dust_positions(current_prices)
    
    # Position should still exist (cleanup failed)
    assert "ERROR" in portfolio.positions
