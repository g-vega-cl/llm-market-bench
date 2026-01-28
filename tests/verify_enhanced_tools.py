import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add apps/engine to path
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from core.llm.tools import execute_price_history_tool, execute_position_pnl_tool

class TestEnhancedTools(unittest.IsolatedAsyncioTestCase):
    async def test_price_history_tool(self):
        print("\n--- Testing get_price_history tool ---")
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"fetched_at": "2026-01-27T10:00:00Z", "price": 150.0},
            {"fetched_at": "2026-01-26T10:00:00Z", "price": 145.0}
        ]
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase):
            result = await execute_price_history_tool("AAPL", days=2)
            print(result)
            self.assertIn("AAPL", result)
            self.assertIn("150.00", result)
            self.assertIn("145.00", result)

    async def test_position_pnl_tool(self):
        print("\n--- Testing get_position_pnl tool ---")
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "ticker": "TSLA",
                "quantity": 10,
                "average_cost_basis": 200.0,
                "current_price": 210.0,
                "unrealized_pnl_usd": 100.0,
                "unrealized_pnl_pct": 5.0
            }
        ]
        
        with patch('core.llm.tools.get_supabase_client', return_value=mock_supabase):
            result = await execute_position_pnl_tool("TSLA", owner_id="test_model")
            print(result)
            self.assertIn("TSLA", result)
            self.assertIn("100.00", result)
            self.assertIn("5.00%", result)

if __name__ == "__main__":
    unittest.main()
