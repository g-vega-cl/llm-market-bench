import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add apps/engine to path
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from core.llm.tools import execute_sell_quantity_tool

class TestSellTools(unittest.IsolatedAsyncioTestCase):
    async def test_sell_25_percent(self):
        mock_supabase = MagicMock()
        # Mock position data: 100 shares at $200 each ($20k value)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"quantity": 100, "current_price": 200.0}
        ]
        
        # Mock Portfolio and its metrics
        mock_portfolio = MagicMock()
        mock_portfolio.initialize = AsyncMock()
        mock_portfolio.positions = {}
        # Total equity $100k, so 10% floor is $10k
        mock_metrics = MagicMock()
        mock_metrics.total_equity = 100000.0
        mock_portfolio.calculate_reg_t_metrics.return_value = mock_metrics
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase), \
             patch('execution.portfolio.Portfolio', return_value=mock_portfolio):
            
            # Selling 25% of 100 shares = 25 shares. Remaining 75 shares * $200 = $15k.
            # $15k > $10k (floor), so it should be a partial sell.
            result = await execute_sell_quantity_tool("AAPL", owner_id="test_model", percentage=25)
            self.assertIn("Recommended SELL Quantity: 25 shares", result)
            self.assertIn("Remaining Position: 75 shares", result)

    async def test_sell_dust_liquidation(self):
        mock_supabase = MagicMock()
        # Mock position data: 60 shares at $200 each ($12k value)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"quantity": 60, "current_price": 200.0}
        ]
        
        mock_portfolio = MagicMock()
        mock_portfolio.initialize = AsyncMock()
        mock_portfolio.positions = {}
        # Total equity $100k, so 10% floor is $10k
        mock_metrics = MagicMock()
        mock_metrics.total_equity = 100000.0
        mock_portfolio.calculate_reg_t_metrics.return_value = mock_metrics
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase), \
             patch('execution.portfolio.Portfolio', return_value=mock_portfolio):
            
            # Selling 50% of 60 shares = 30 shares. Remaining 30 shares * $200 = $6k.
            # $6k < $10k (floor), so it should mandate a 100% sell.
            result = await execute_sell_quantity_tool("AAPL", owner_id="test_model", percentage=50)
            self.assertIn("Recommended SELL Quantity: 60 shares", result)
            self.assertIn("Remaining Position: 0 shares", result)
            self.assertIn("mandated a 100% (FULL) sell", result)

    async def test_sell_100_percent(self):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"quantity": 123, "current_price": 100.0}
        ]
        
        mock_portfolio = MagicMock()
        mock_portfolio.initialize = AsyncMock()
        # Mock metrics to ensure floor doesn't block (though 100% sell always works)
        mock_metrics = MagicMock()
        mock_metrics.total_equity = 50000.0
        mock_portfolio.calculate_reg_t_metrics.return_value = mock_metrics
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase), \
             patch('execution.portfolio.Portfolio', return_value=mock_portfolio):
            result = await execute_sell_quantity_tool("AAPL", owner_id="test_model", percentage=100)
            self.assertIn("Recommended SELL Quantity: 123 shares", result)

    async def test_no_position(self):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase):
            result = await execute_sell_quantity_tool("TSLA", owner_id="test_model", percentage=100)
            self.assertIn("Error: You do not currently own a position in TSLA", result)

if __name__ == "__main__":
    unittest.main()
