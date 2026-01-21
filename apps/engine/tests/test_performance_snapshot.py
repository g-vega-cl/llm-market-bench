"""Tests for Daily Performance Snapshotting."""

import pytest
from unittest.mock import MagicMock, patch
from execution.portfolio import Portfolio, Position

@pytest.mark.asyncio
async def test_record_performance_snapshot():
    """Test recording a performance snapshot to the DB."""
    p = Portfolio("test_agent")
    p.id = "portfolio-123"
    p.cash_balance = 5000.00
    p.positions = {"AAPL": Position("AAPL", 10, 150.00)}
    
    current_prices = {"AAPL": 200.00}
    
    # Expected Equity: 5000 + (10 * 200) = 7000.00
    
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    
    # Mock upsert success
    mock_res = MagicMock()
    mock_res.data = [{"id": "snapshot-123"}]
    mock_table.upsert.return_value.execute.return_value = mock_res
    
    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        await p.record_performance_snapshot(current_prices)
        
        # Verify upsert call
        mock_table.upsert.assert_called_once()
        call_args = mock_table.upsert.call_args[0][0]
        
        assert call_args["portfolio_id"] == "portfolio-123"
        assert call_args["total_equity"] == pytest.approx(7000.00)
        assert call_args["cash_balance"] == 5000.00
        # Stock Value = 2000. IM (50%) = 1000. Equity = 7000. Avail = 6000. BP = 24000.
        assert call_args["buying_power"] == pytest.approx(24000.00)
        assert call_args["initial_margin_req"] == 1000.00
        assert call_args["maintenance_margin_req"] == 500.00
        assert call_args["available_funds"] == 6000.00
        assert call_args["excess_liquidity"] == 6500.00
        from datetime import date
        today = date.today().isoformat()
        assert call_args["date"] == today

@pytest.mark.asyncio
async def test_record_performance_snapshot_idempotency():
    """Test that upsert is used for idempotency."""
    p = Portfolio("test_agent")
    p.id = "portfolio-123"
    
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    
    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        await p.record_performance_snapshot({})
        
        # Upsert should be called once
        assert mock_table.upsert.called
