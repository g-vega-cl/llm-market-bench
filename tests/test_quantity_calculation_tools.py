import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add apps/engine to path
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from core.llm.tools import execute_buy_quantity_tool, execute_sell_quantity_tool

class TestQuantityCalculationTools(unittest.IsolatedAsyncioTestCase):
    
    # --- BUY TOOL TESTS ---
    
    async def test_buy_quantity_upsize_to_floor(self):
        """Test that buys are upsized to the 10% equity floor."""
        mock_portfolio = MagicMock()
        mock_portfolio.initialize = AsyncMock()
        mock_portfolio.positions = {}
        
        # Scenario: $100k Total Equity, $50k Buying Power. 
        # Requested 5% of BP ($2.5k). 10% Floor is $10k.
        mock_metrics = MagicMock()
        mock_metrics.total_equity = 100000.0
        mock_metrics.buying_power = 50000.0
        mock_portfolio.calculate_reg_t_metrics.return_value = mock_metrics
        
        mock_manager = MagicMock()
        mock_quote = MagicMock()
        mock_quote.exists = True
        mock_quote.price = 100.0
        mock_manager.get_quote = AsyncMock(return_value=mock_quote)
        
        with patch('execution.portfolio.Portfolio', return_value=mock_portfolio), \
             patch('core.llm.tools.MarketDataManager', return_value=mock_manager):
            
            # Requesting 5% of $50k = $2.5k. 
            # But Floor is $10k. Tool should recommend 100 shares ($10k).
            result = await execute_buy_quantity_tool("AAPL", owner_id="test_model", percentage=5)
            
            self.assertIn("Recommended BUY Quantity: 100 shares", result)
            self.assertIn("was below the 10% Total Equity Floor", result)
            self.assertIn("automatically upsized", result)

    async def test_buy_quantity_capped_at_bp(self):
        """Test that buys are capped at available buying power even if below floor."""
        mock_portfolio = MagicMock()
        mock_portfolio.initialize = AsyncMock()
        mock_portfolio.positions = {}
        
        # Scenario: $100k Total Equity, only $5k Buying Power left.
        # Requested 100% of BP ($5k). 10% Floor is $10k.
        # Should cap at $5k.
        mock_metrics = MagicMock()
        mock_metrics.total_equity = 100000.0
        mock_metrics.buying_power = 5000.0
        mock_portfolio.calculate_reg_t_metrics.return_value = mock_metrics
        
        mock_manager = MagicMock()
        mock_quote = MagicMock()
        mock_quote.exists = True
        mock_quote.price = 100.0
        mock_manager.get_quote = AsyncMock(return_value=mock_quote)
        
        with patch('execution.portfolio.Portfolio', return_value=mock_portfolio), \
             patch('core.llm.tools.MarketDataManager', return_value=mock_manager):
            
            result = await execute_buy_quantity_tool("AAPL", owner_id="test_model", percentage=100)
            
            self.assertIn("Recommended BUY Quantity: 50 shares", result)
            self.assertIn("WARNING: Insufficient Buying Power", result)

    # --- SELL TOOL TESTS ---

    async def test_sell_quantity_partial(self):
        """Test a normal partial sell where remaining balance > floor."""
        mock_supabase = MagicMock()
        # Holding 200 shares at $100 = $20k.
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"quantity": 200, "current_price": 100.0}
        ]
        
        mock_portfolio = MagicMock()
        mock_portfolio.initialize = AsyncMock()
        mock_portfolio.positions = {}
        # $100k equity -> $10k floor.
        mock_metrics = MagicMock()
        mock_metrics.total_equity = 100000.0
        mock_portfolio.calculate_reg_t_metrics.return_value = mock_metrics
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase), \
             patch('execution.portfolio.Portfolio', return_value=mock_portfolio):
            
            # Sell 50% (100 shares). Remaining 100 shares * $100 = $10k.
            # $10k == floor. Should be allowed as partial.
            result = await execute_sell_quantity_tool("AAPL", owner_id="test_model", percentage=50)
            
            self.assertIn("Recommended SELL Quantity: 100 shares", result)
            self.assertIn("Remaining Position: 100 shares", result)
            self.assertNotIn("mandated a 100% (FULL) sell", result)

    async def test_sell_quantity_dust_cleanup(self):
        """Test that a partial sell is forced to 100% if remaining < floor."""
        mock_supabase = MagicMock()
        # Holding 150 shares at $100 = $15k.
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"quantity": 150, "current_price": 100.0}
        ]
        
        mock_portfolio = MagicMock()
        mock_portfolio.initialize = AsyncMock()
        mock_portfolio.positions = {}
        # $100k equity -> $10k floor.
        mock_metrics = MagicMock()
        mock_metrics.total_equity = 100000.0
        mock_portfolio.calculate_reg_t_metrics.return_value = mock_metrics
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase), \
             patch('execution.portfolio.Portfolio', return_value=mock_portfolio):
            
            # Sell 50% (75 shares). Remaining 75 shares * $100 = $7.5k.
            # $7.5k < $10k floor. Tool should force 100% sell.
            result = await execute_sell_quantity_tool("AAPL", owner_id="test_model", percentage=50)
            
            self.assertIn("Recommended SELL Quantity: 150 shares", result)
            self.assertIn("Remaining Position: 0 shares", result)
            self.assertIn("To prevent 'dust' positions, this tool has mandated a 100% (FULL) sell", result)

if __name__ == "__main__":
    unittest.main()
