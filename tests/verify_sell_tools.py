import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add apps/engine to path
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from core.llm.tools import execute_sell_20_percent_tool, execute_sell_50_percent_tool, execute_sell_100_percent_tool

class TestSellTools(unittest.IsolatedAsyncioTestCase):
    async def test_sell_20_percent(self):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"quantity": 100}
        ]
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase):
            result = await execute_sell_20_percent_tool("AAPL", owner_id="test_model")
            self.assertIn("Recommended Sell Quantity: 20 shares", result)
            self.assertIn("Current Holdings: 100 shares", result)

    async def test_sell_50_percent(self):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"quantity": 100}
        ]
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase):
            result = await execute_sell_50_percent_tool("AAPL", owner_id="test_model")
            self.assertIn("Recommended Sell Quantity: 50 shares", result)

    async def test_sell_100_percent(self):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"quantity": 123}
        ]
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase):
            result = await execute_sell_100_percent_tool("AAPL", owner_id="test_model")
            self.assertIn("Recommended Sell Quantity: 123 shares", result)

    async def test_no_position(self):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase):
            result = await execute_sell_100_percent_tool("TSLA", owner_id="test_model")
            self.assertIn("Error: You do not currently own a position in TSLA", result)

    async def test_rounding_edge_case(self):
        mock_supabase = MagicMock()
        # 20% of 3 shares is 0.6, should round to 1 (at least 1 share if percentage > 0)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"quantity": 3}
        ]
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase):
            result = await execute_sell_20_percent_tool("AAPL", owner_id="test_model")
            self.assertIn("Recommended Sell Quantity: 1 shares", result)

if __name__ == "__main__":
    unittest.main()
