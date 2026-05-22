import sys
import os

# Add apps/engine to path BEFORE importing any engine or local modules
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from execution.portfolio import Portfolio, Position


class TestPortfolioPnL(unittest.IsolatedAsyncioTestCase):
    async def test_execute_trade_calculates_pnl(self):
        # Setup portfolio
        portfolio = Portfolio("test_agent")
        portfolio.id = uuid4()
        portfolio.cash_balance = 10000.0

        # Add a position
        # Bought 100 shares at $100 -> Cost Basis = $100
        portfolio.positions["AAPL"] = Position(
            ticker="AAPL", quantity=100, average_cost_basis=100.0
        )

        mock_supabase = MagicMock()
        # Mock the trades table insert to capture what was sent
        mock_insert = mock_supabase.table.return_value.insert
        mock_insert.return_value.execute.return_value.data = [{"id": uuid4()}]

        with patch(
            "execution.portfolio.get_supabase_client", return_value=mock_supabase
        ):
            # Execute a SELL trade at $120 (Profit of $20/share)
            # Sell 50 shares
            await portfolio.execute_trade("AAPL", 50, 120.0, "SELL")

            # Verify the data sent to the trades table
            self.assertTrue(mock_insert.called)
            inserted_data = mock_insert.call_args[0][0]

            # Expected PnL: (120 - 100) * 50 = 1000
            # Expected PnL %: ((120 / 100) - 1) * 100 = 20%
            self.assertAlmostEqual(inserted_data["realized_pnl"], 1000.0)
            self.assertAlmostEqual(inserted_data["realized_pnl_pct"], 20.0)
            self.assertEqual(inserted_data["signal"], "SELL")

    async def test_execute_trade_no_pnl_on_buy(self):
        portfolio = Portfolio("test_agent")
        portfolio.id = uuid4()
        portfolio.cash_balance = 20000.0

        mock_supabase = MagicMock()
        mock_insert = mock_supabase.table.return_value.insert
        mock_insert.return_value.execute.return_value.data = [{"id": uuid4()}]

        with patch(
            "execution.portfolio.get_supabase_client", return_value=mock_supabase
        ):
            # Execute a BUY trade
            await portfolio.execute_trade("TSLA", 10, 200.0, "BUY")

            inserted_data = mock_insert.call_args[0][0]
            self.assertNotIn("realized_pnl", inserted_data)
            self.assertNotIn("realized_pnl_pct", inserted_data)


if __name__ == "__main__":
    unittest.main()
