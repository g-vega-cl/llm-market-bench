
import pytest
from unittest.mock import MagicMock, patch
from execution.portfolio import Portfolio, Position

@pytest.mark.asyncio
async def test_execute_trade_sell_unheld_ticker():
    """Test that selling a ticker not in the portfolio is rejected."""
    p = Portfolio("test_agent")
    p.id = "portfolio-123"
    p.positions = {} # Empty portfolio
    
    mock_db = MagicMock()
    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        trade_id = await p.execute_trade("AAPL", 10, 150.0, "SELL")
        
    assert trade_id is None
    assert "AAPL" not in p.positions
    # Verify NO DB update was called (since it returned early)
    assert not mock_db.table.called

@pytest.mark.asyncio
async def test_execute_trade_sell_more_than_held():
    """Test that selling more than held is capped to owned quantity."""
    p = Portfolio("test_agent")
    p.id = "portfolio-123"
    p.positions = {"AAPL": Position("AAPL", 10, 100.0)}
    p.cash_balance = 0.0
    
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    
    # Mock portfolios update chain
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
    # Mock positions delete/upsert chain
    mock_table.delete.return_value.match.return_value.execute.return_value = MagicMock()
    
    # Mock trades insert response
    mock_res_trade = MagicMock()
    mock_res_trade.data = [{"id": "trade-456"}]
    mock_table.insert.return_value.execute.return_value = mock_res_trade

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        trade_id = await p.execute_trade("AAPL", 50, 200.0, "SELL")
        
    assert trade_id == "trade-456"
    assert "AAPL" not in p.positions # Because 50 was capped to 10
    assert p.cash_balance == 2000.0
    
    # Verify trade was inserted with qty 10
    args, kwargs = mock_table.insert.call_args
    assert args[0]["quantity"] == 10
    assert args[0]["total_cost"] == 2000.0


@pytest.mark.asyncio
async def test_execute_trade_sell_partial():
    """Test that partial sell correctly updates quantity and cash."""
    p = Portfolio("test_agent")
    p.id = "portfolio-123"
    p.positions = {"AAPL": Position("AAPL", 10, 100.0)}
    p.cash_balance = 0.0
    
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    
    mock_res_trade = MagicMock()
    mock_res_trade.data = [{"id": "trade-789"}]
    mock_table.insert.return_value.execute.return_value = mock_res_trade

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        trade_id = await p.execute_trade("AAPL", 4, 150.0, "SELL")
        
    assert trade_id == "trade-789"
    assert p.positions["AAPL"].quantity == 6
    # Cash: 4 * 150 = 600
    assert p.cash_balance == 600.0
