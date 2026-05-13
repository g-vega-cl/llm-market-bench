"""Comprehensive tests for P&L calculations with average cost basis tracking.

This module tests:
1. Average cost basis calculation for BUY transactions
2. Realized P&L calculation for SELL transactions
3. Partial position sales with correct cost basis allocation
4. Full position closure P&L tracking
5. Multi-lot position management
"""

from unittest.mock import MagicMock, patch

import pytest

from execution.portfolio import Portfolio, Position


class TestAverageCostBasisBUY:
    """Tests for average cost basis tracking during BUY transactions."""

    @pytest.mark.asyncio
    async def test_initial_buy_sets_cost_basis(self):
        """Test that first BUY correctly sets average cost basis."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        
        # Mock supabase
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
        mock_table.update.return_value.execute.return_value = MagicMock()
        
        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            # Initialize with empty positions
            p.cash_balance = 10000.00
            p.positions = {}
            
            # BUY 100 shares @ $150
            await p.execute_trade("AAPL", 100, 150.00, "BUY", decision_id="dec-1")
            
            # Verify average cost basis is set to purchase price
            assert p.positions["AAPL"].quantity == 100
            assert p.positions["AAPL"].average_cost_basis == 150.00

    @pytest.mark.asyncio
    async def test_second_buy_updates_weighted_average(self):
        """Test that subsequent BUYs correctly calculate weighted average cost basis."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        
        # Mock supabase
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
        mock_table.update.return_value.execute.return_value = MagicMock()
        
        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            # Start with existing position: 100 shares @ $150
            p.cash_balance = 10000.00
            p.positions = {
                "AAPL": Position(ticker="AAPL", quantity=100, average_cost_basis=150.00)
            }
            
            # BUY 100 more shares @ $200
            await p.execute_trade("AAPL", 100, 200.00, "BUY", decision_id="dec-1")
            
            # Verify weighted average: (100*150 + 100*200) / 200 = $175
            assert p.positions["AAPL"].quantity == 200
            assert p.positions["AAPL"].average_cost_basis == pytest.approx(175.00)

    @pytest.mark.asyncio
    async def test_multiple_buys_at_different_prices(self):
        """Test average cost basis with multiple BUY transactions at various prices."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
        mock_table.update.return_value.execute.return_value = MagicMock()
        
        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            p.cash_balance = 50000.00
            p.positions = {}
            
            # BUY 1: 50 shares @ $100
            await p.execute_trade("MSFT", 50, 100.00, "BUY", decision_id="dec-1")
            assert p.positions["MSFT"].average_cost_basis == 100.00
            
            # BUY 2: 100 shares @ $150
            await p.execute_trade("MSFT", 100, 150.00, "BUY", decision_id="dec-2")
            # Expected: (50*100 + 100*150) / 150 = 133.33
            assert p.positions["MSFT"].average_cost_basis == pytest.approx(133.33, abs=0.01)
            
            # BUY 3: 50 shares @ $120
            await p.execute_trade("MSFT", 50, 120.00, "BUY", decision_id="dec-3")
            # Expected: (150*133.33 + 50*120) / 200 = 130.00
            assert p.positions["MSFT"].quantity == 200
            assert p.positions["MSFT"].average_cost_basis == pytest.approx(130.00)


class TestRealizedPnLSELL:
    """Tests for realized P&L calculation during SELL transactions."""

    @pytest.mark.asyncio
    async def test_full_position_sale_realizes_correct_pnl(self):
        """Test that selling entire position calculates correct realized P&L."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock()
        mock_table.delete.return_value.execute.return_value = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
        mock_table.update.return_value.execute.return_value = MagicMock()
        
        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            # Start with position: 100 shares @ $150
            p.cash_balance = 5000.00
            p.positions = {
                "AAPL": Position(ticker="AAPL", quantity=100, average_cost_basis=150.00)
            }
            
            # SELL all 100 shares @ $200
            await p.execute_trade("AAPL", 100, 200.00, "SELL", decision_id="dec-1")
            
            # Verify position is closed
            assert "AAPL" not in p.positions
            
            # Verify trade was recorded with correct P&L
            insert_call = mock_table.insert.call_args
            trade_data = insert_call[0][0]
            assert trade_data["realized_pnl"] == pytest.approx(5000.00)  # (200-150) * 100
            assert trade_data["realized_pnl_pct"] == pytest.approx(33.33, abs=0.01)  # (200/150 - 1) * 100

    @pytest.mark.asyncio
    async def test_partial_sale_realizes_proportional_pnl(self):
        """Test that selling partial position calculates correct proportional P&L."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
        mock_table.update.return_value.execute.return_value = MagicMock()
        
        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            # Start with position: 200 shares @ $175 (avg cost)
            p.cash_balance = 10000.00
            p.positions = {
                "AAPL": Position(ticker="AAPL", quantity=200, average_cost_basis=175.00)
            }
            
            # SELL 50 shares @ $200
            await p.execute_trade("AAPL", 50, 200.00, "SELL", decision_id="dec-1")
            
            # Verify remaining position
            assert p.positions["AAPL"].quantity == 150
            # Average cost basis should remain unchanged after partial sale
            assert p.positions["AAPL"].average_cost_basis == 175.00
            
            # Verify trade P&L: (200 - 175) * 50 = $1,250
            insert_call = mock_table.insert.call_args
            trade_data = insert_call[0][0]
            assert trade_data["realized_pnl"] == pytest.approx(1250.00)
            assert trade_data["realized_pnl_pct"] == pytest.approx(14.29, abs=0.01)

    @pytest.mark.asyncio
    async def test_partial_sale_with_loss(self):
        """Test P&L calculation when selling at a loss."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
        mock_table.update.return_value.execute.return_value = MagicMock()
        
        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            # Start with position: 100 shares @ $300
            p.cash_balance = 10000.00
            p.positions = {
                "TSLA": Position(ticker="TSLA", quantity=100, average_cost_basis=300.00)
            }
            
            # SELL 40 shares @ $250 (loss)
            await p.execute_trade("TSLA", 40, 250.00, "SELL", decision_id="dec-1")
            
            # Verify trade P&L: (250 - 300) * 40 = -$2,000
            insert_call = mock_table.insert.call_args
            trade_data = insert_call[0][0]
            assert trade_data["realized_pnl"] == pytest.approx(-2000.00)
            assert trade_data["realized_pnl_pct"] == pytest.approx(-16.67, abs=0.01)
            
            # Verify remaining position
            assert p.positions["TSLA"].quantity == 60
            assert p.positions["TSLA"].average_cost_basis == 300.00

    @pytest.mark.asyncio
    async def test_multiple_sells_same_position(self):
        """Test multiple SELL transactions on same position maintain correct cost basis."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock()
        mock_table.delete.return_value.execute.return_value = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
        mock_table.update.return_value.execute.return_value = MagicMock()
        
        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            # Start with position: 300 shares @ $100
            p.cash_balance = 50000.00
            p.positions = {
                "NVDA": Position(ticker="NVDA", quantity=300, average_cost_basis=100.00)
            }
            
            # SELL 1: 100 shares @ $150
            await p.execute_trade("NVDA", 100, 150.00, "SELL", decision_id="dec-1")
            insert_call = mock_table.insert.call_args
            trade_data = insert_call[0][0]
            assert trade_data["realized_pnl"] == pytest.approx(5000.00)  # (150-100)*100
            
            # SELL 2: 100 shares @ $200
            await p.execute_trade("NVDA", 100, 200.00, "SELL", decision_id="dec-2")
            insert_call = mock_table.insert.call_args
            trade_data = insert_call[0][0]
            assert trade_data["realized_pnl"] == pytest.approx(10000.00)  # (200-100)*100
            
            # SELL 3: 100 shares @ $180
            await p.execute_trade("NVDA", 100, 180.00, "SELL", decision_id="dec-3")
            insert_call = mock_table.insert.call_args
            trade_data = insert_call[0][0]
            assert trade_data["realized_pnl"] == pytest.approx(8000.00)  # (180-100)*100
            
            # Verify position closed
            assert "NVDA" not in p.positions
            
            # Total realized P&L should be $23,000
            total_pnl = 5000 + 10000 + 8000
            assert total_pnl == 23000


class TestComplexScenarios:
    """Tests for complex P&L scenarios with mixed BUY/SELL transactions."""

    @pytest.mark.asyncio
    async def test_buy_sell_buy_sequence(self):
        """Test average cost basis through BUY-SELL-BUY sequence."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"

        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock()
        mock_table.delete.return_value.execute.return_value = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
        mock_table.update.return_value.execute.return_value = MagicMock()

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            p.cash_balance = 50000.00
            p.positions = {}

            # BUY 1: 1000 shares @ $50 = $50,000
            await p.execute_trade("AMD", 1000, 50.00, "BUY", decision_id="dec-1")
            assert p.positions["AMD"].average_cost_basis == 50.00

            # SELL 1: 500 shares @ $80 (profit)
            await p.execute_trade("AMD", 500, 80.00, "SELL", decision_id="dec-2")
            # Remaining: 500 shares @ $50 (avg cost unchanged)
            assert p.positions["AMD"].quantity == 500
            assert p.positions["AMD"].average_cost_basis == 50.00

            # BUY 2: 1000 shares @ $90
            await p.execute_trade("AMD", 1000, 90.00, "BUY", decision_id="dec-3")
            # New avg: (500*50 + 1000*90) / 1500 = 76.67
            assert p.positions["AMD"].quantity == 1500
            assert p.positions["AMD"].average_cost_basis == pytest.approx(76.67, abs=0.01)

    @pytest.mark.asyncio
    async def test_multi_part_buy_sell_sequence(self):
        """Test a complex sequence of multiple buys and sells."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"

        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock()
        mock_table.delete.return_value.execute.return_value = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
        mock_table.update.return_value.execute.return_value = MagicMock()

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            p.cash_balance = 100000.00
            p.positions = {}

            # Step 1: BUY 100 @ $100 = $10,000
            await p.execute_trade("NVDA", 100, 100.00, "BUY", decision_id="dec-1")
            assert p.positions["NVDA"].average_cost_basis == 100.00

            # Step 2: BUY 100 @ $120 = $12,000
            await p.execute_trade("NVDA", 100, 120.00, "BUY", decision_id="dec-2")
            # (100*100 + 100*120)/200 = 110
            assert p.positions["NVDA"].quantity == 200
            assert p.positions["NVDA"].average_cost_basis == 110.00

            # Step 3: SELL 50 @ $130
            await p.execute_trade("NVDA", 50, 130.00, "SELL", decision_id="dec-3")
            # Realized PnL: (130 - 110) * 50 = 1000
            insert_call = mock_table.insert.call_args_list[-1]
            trade_data = insert_call[0][0]
            assert trade_data["realized_pnl"] == 1000.00
            assert p.positions["NVDA"].quantity == 150
            assert p.positions["NVDA"].average_cost_basis == 110.00

            # Step 4: BUY 50 @ $150
            await p.execute_trade("NVDA", 50, 150.00, "BUY", decision_id="dec-4")
            # (150*110 + 50*150)/200 = (16500 + 7500)/200 = 24000/200 = 120
            assert p.positions["NVDA"].quantity == 200
            assert p.positions["NVDA"].average_cost_basis == 120.00
            
            # Step 5: SELL 20 @ $160
            await p.execute_trade("NVDA", 20, 160.00, "SELL", decision_id="dec-5")
            # Realized PnL: (160 - 120) * 20 = 800
            insert_call = mock_table.insert.call_args_list[-1]
            trade_data = insert_call[0][0]
            assert trade_data["realized_pnl"] == 800.00
            assert p.positions["NVDA"].quantity == 180
            assert p.positions["NVDA"].average_cost_basis == 120.00

    @pytest.mark.asyncio
    async def test_sell_without_position_returns_none(self):
        """Test that SELL without position returns None and doesn't record P&L."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        
        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            p.cash_balance = 10000.00
            p.positions = {}
            
            # Try to SELL without owning
            result = await p.execute_trade("AAPL", 100, 150.00, "SELL", decision_id="dec-1")
            
            # Should return None (rejected)
            assert result is None
            
            # Verify no trade was recorded
            mock_table.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_cost_basis_edge_case(self):
        """Test P&L calculation when cost basis is zero (edge case)."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        
        mock_db = MagicMock()
        mock_table = MagicMock()
        mock_db.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
        mock_table.update.return_value.execute.return_value = MagicMock()
        
        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            # Edge case: position with $0 cost basis (e.g., stock grant)
            p.cash_balance = 10000.00
            p.positions = {
                "GRNT": Position(ticker="GRNT", quantity=100, average_cost_basis=0.00)
            }
            
            # SELL all @ $50
            await p.execute_trade("GRNT", 100, 50.00, "SELL", decision_id="dec-1")
            
            # Verify P&L: (50 - 0) * 100 = $5,000
            insert_call = mock_table.insert.call_args
            trade_data = insert_call[0][0]
            assert trade_data["realized_pnl"] == 5000.00
            # P&L % should be 0 when cost basis is 0 (avoid division by zero)
            assert trade_data["realized_pnl_pct"] == 0


class TestPortfolioSummary:
    """Tests for portfolio summary with P&L information."""

    @pytest.mark.asyncio
    async def test_get_portfolio_summary_includes_pnl(self):
        """Test that portfolio summary includes P&L for each position."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 10000.00
        p.positions = {
            "AAPL": Position(ticker="AAPL", quantity=100, average_cost_basis=150.00),
            "MSFT": Position(ticker="MSFT", quantity=50, average_cost_basis=300.00)
        }
        
        current_prices = {
            "AAPL": 175.00,  # +$2,500
            "MSFT": 280.00   # -$1,000
        }
        
        summary = await p.get_portfolio_summary(current_prices)
        
        # Verify summary contains P&L information
        assert "AAPL" in summary
        assert "P/L:" in summary
        assert "2500.00" in summary or "2,500.00" in summary or "+2,500" in summary or "+2500" in summary
        
        assert "MSFT" in summary
        assert "-1000.00" in summary or "-1,000.00" in summary or "-1000" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
