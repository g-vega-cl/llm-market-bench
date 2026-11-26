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
        # The portfolio now ledgers trades through the execute_portfolio_trade RPC.
        mock_rpc = mock_supabase.rpc
        mock_rpc.return_value.execute.return_value.data = {
            "trade_id": str(uuid4()),
            "cash_balance": 9400.0,
            "position_quantity": 50,
            "position_avg_cost": 100.0,
        }

        with patch(
            "execution.portfolio.get_supabase_client", return_value=mock_supabase
        ):
            # Execute a SELL trade at $120 (Profit of $20/share)
            # Sell 50 shares
            trade_id = await portfolio.execute_trade("AAPL", 50, 120.0, "SELL")

            # Verify the RPC was called with the trade payload
            self.assertTrue(mock_rpc.called)
            rpc_name, rpc_params = mock_rpc.call_args[0]
            self.assertEqual(rpc_name, "execute_portfolio_trade")
            self.assertEqual(rpc_params["p_ticker"], "AAPL")
            self.assertEqual(rpc_params["p_signal"], "SELL")
            self.assertEqual(rpc_params["p_quantity"], 50)
            self.assertAlmostEqual(rpc_params["p_price"], 120.0)
            self.assertIsNotNone(trade_id)

            # PnL is calculated server-side by the RPC; the client only sends
            # price, quantity, and signal.
            self.assertNotIn("realized_pnl", rpc_params)
            self.assertNotIn("realized_pnl_pct", rpc_params)

    async def test_execute_trade_no_pnl_on_buy(self):
        portfolio = Portfolio("test_agent")
        portfolio.id = uuid4()
        portfolio.cash_balance = 20000.0

        mock_supabase = MagicMock()
        mock_rpc = mock_supabase.rpc
        mock_rpc.return_value.execute.return_value.data = {
            "trade_id": str(uuid4()),
            "cash_balance": 18000.0,
            "position_quantity": 10,
            "position_avg_cost": 200.0,
        }

        with patch(
            "execution.portfolio.get_supabase_client", return_value=mock_supabase
        ):
            # Execute a BUY trade
            trade_id = await portfolio.execute_trade("TSLA", 10, 200.0, "BUY")

            self.assertTrue(mock_rpc.called)
            rpc_name, rpc_params = mock_rpc.call_args[0]
            self.assertEqual(rpc_name, "execute_portfolio_trade")
            self.assertEqual(rpc_params["p_signal"], "BUY")
            self.assertEqual(rpc_params["p_quantity"], 10)
            self.assertAlmostEqual(rpc_params["p_price"], 200.0)
            self.assertIsNotNone(trade_id)
            self.assertNotIn("realized_pnl", rpc_params)
            self.assertNotIn("realized_pnl_pct", rpc_params)


if __name__ == "__main__":
    unittest.main()
