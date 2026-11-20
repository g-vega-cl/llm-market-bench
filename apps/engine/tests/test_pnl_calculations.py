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


def _make_rpc_db(portfolio: Portfolio) -> MagicMock:
    """Create a hermetic Supabase RPC mock backed by the test portfolio's state."""
    recorded_trades: list[dict] = []
    positions: dict[str, dict] = {
        t: {"quantity": p.quantity, "average_cost_basis": p.average_cost_basis} for t, p in portfolio.positions.items()
    }
    state = {"cash": portfolio.cash_balance, "seq": 0}

    def rpc_side_effect(_name: str, params: dict):
        ticker = params["p_ticker"]
        sig = params["p_signal"]
        qty = int(params["p_quantity"])
        price = float(params["p_price"])
        cost = qty * price
        realized_pnl = None
        realized_pnl_pct = None

        if sig == "BUY":
            state["cash"] -= cost
            if ticker in positions:
                cur = positions[ticker]
                new_qty = cur["quantity"] + qty
                cur["average_cost_basis"] = ((cur["average_cost_basis"] * cur["quantity"]) + cost) / new_qty
                cur["quantity"] = new_qty
            else:
                positions[ticker] = {"quantity": qty, "average_cost_basis": price}
        else:
            cur = positions[ticker]
            qty = min(qty, cur["quantity"])
            cost = qty * price
            avg_cost = cur["average_cost_basis"]
            realized_pnl = (price - avg_cost) * qty
            realized_pnl_pct = ((price / avg_cost) - 1) * 100 if avg_cost > 0 else 0.0
            state["cash"] += cost
            cur["quantity"] -= qty
            if cur["quantity"] == 0:
                positions.pop(ticker)

        state["seq"] += 1
        trade_id = f"trade-{state['seq']}"
        recorded_trades.append(
            {
                "id": trade_id,
                "ticker": ticker,
                "signal": sig,
                "quantity": qty,
                "price": price,
                "total_cost": cost,
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct,
            }
        )
        pos = positions.get(ticker, {})
        call_mock = MagicMock()
        call_mock.execute.return_value = MagicMock(
            data={
                "trade_id": trade_id,
                "cash_balance": state["cash"],
                "sma": max(0.0, state["cash"]),
                "quantity": qty,
                "total_cost": cost,
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct,
                "position_quantity": pos.get("quantity", 0),
                "position_avg_cost": pos.get("average_cost_basis", 0.0),
                "idempotent_replay": False,
            }
        )
        return call_mock

    mock_db = MagicMock()
    mock_db.rpc.side_effect = rpc_side_effect
    mock_db.recorded_trades = recorded_trades
    return mock_db


class TestAverageCostBasisBUY:
    """Tests for average cost basis tracking during BUY transactions."""

    @pytest.mark.asyncio
    async def test_initial_buy_sets_cost_basis(self):
        """Test that first BUY correctly sets average cost basis."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 20000.00
        p.positions = {}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            await p.execute_trade("AAPL", 100, 150.00, "BUY", decision_id="dec-1", skip_alpaca_mirror=True)
            assert p.positions["AAPL"].quantity == 100
            assert p.positions["AAPL"].average_cost_basis == 150.00

    @pytest.mark.asyncio
    async def test_second_buy_updates_weighted_average(self):
        """Test that subsequent BUYs correctly calculate weighted average cost basis."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 25000.00
        p.positions = {"AAPL": Position(ticker="AAPL", quantity=100, average_cost_basis=150.00)}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            await p.execute_trade("AAPL", 100, 200.00, "BUY", decision_id="dec-1", skip_alpaca_mirror=True)
            assert p.positions["AAPL"].quantity == 200
            assert p.positions["AAPL"].average_cost_basis == pytest.approx(175.00)

    @pytest.mark.asyncio
    async def test_multiple_buys_at_different_prices(self):
        """Test average cost basis with multiple BUY transactions at various prices."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 100000.00
        p.positions = {}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            await p.execute_trade("MSFT", 50, 100.00, "BUY", decision_id="dec-1", skip_alpaca_mirror=True)
            assert p.positions["MSFT"].average_cost_basis == 100.00

            await p.execute_trade("MSFT", 100, 150.00, "BUY", decision_id="dec-2", skip_alpaca_mirror=True)
            assert p.positions["MSFT"].average_cost_basis == pytest.approx(133.33, abs=0.01)

            await p.execute_trade("MSFT", 50, 120.00, "BUY", decision_id="dec-3", skip_alpaca_mirror=True)
            assert p.positions["MSFT"].quantity == 200
            assert p.positions["MSFT"].average_cost_basis == pytest.approx(130.00)


class TestRealizedPnLSELL:
    """Tests for realized P&L calculation during SELL transactions."""

    @pytest.mark.asyncio
    async def test_full_position_sale_realizes_correct_pnl(self):
        """Test that selling entire position calculates correct realized P&L."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 5000.00
        p.positions = {"AAPL": Position(ticker="AAPL", quantity=100, average_cost_basis=150.00)}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            await p.execute_trade("AAPL", 100, 200.00, "SELL", decision_id="dec-1", skip_alpaca_mirror=True)

            assert "AAPL" not in p.positions
            trade_data = mock_db.recorded_trades[-1]
            assert trade_data["realized_pnl"] == pytest.approx(5000.00)
            assert trade_data["realized_pnl_pct"] == pytest.approx(33.33, abs=0.01)

    @pytest.mark.asyncio
    async def test_partial_sale_realizes_proportional_pnl(self):
        """Test that selling partial position calculates correct proportional P&L."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 10000.00
        p.positions = {"AAPL": Position(ticker="AAPL", quantity=200, average_cost_basis=175.00)}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            await p.execute_trade("AAPL", 50, 200.00, "SELL", decision_id="dec-1", skip_alpaca_mirror=True)

            assert p.positions["AAPL"].quantity == 150
            assert p.positions["AAPL"].average_cost_basis == 175.00
            trade_data = mock_db.recorded_trades[-1]
            assert trade_data["realized_pnl"] == pytest.approx(1250.00)
            assert trade_data["realized_pnl_pct"] == pytest.approx(14.29, abs=0.01)

    @pytest.mark.asyncio
    async def test_partial_sale_with_loss(self):
        """Test P&L calculation when selling at a loss."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 10000.00
        p.positions = {"TSLA": Position(ticker="TSLA", quantity=100, average_cost_basis=300.00)}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            await p.execute_trade("TSLA", 40, 250.00, "SELL", decision_id="dec-1", skip_alpaca_mirror=True)

            trade_data = mock_db.recorded_trades[-1]
            assert trade_data["realized_pnl"] == pytest.approx(-2000.00)
            assert trade_data["realized_pnl_pct"] == pytest.approx(-16.67, abs=0.01)
            assert p.positions["TSLA"].quantity == 60
            assert p.positions["TSLA"].average_cost_basis == 300.00

    @pytest.mark.asyncio
    async def test_multiple_sells_same_position(self):
        """Test multiple SELL transactions on same position maintain correct cost basis."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 50000.00
        p.positions = {"NVDA": Position(ticker="NVDA", quantity=300, average_cost_basis=100.00)}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            await p.execute_trade("NVDA", 100, 150.00, "SELL", decision_id="dec-1", skip_alpaca_mirror=True)
            assert mock_db.recorded_trades[-1]["realized_pnl"] == pytest.approx(5000.00)

            await p.execute_trade("NVDA", 100, 200.00, "SELL", decision_id="dec-2", skip_alpaca_mirror=True)
            assert mock_db.recorded_trades[-1]["realized_pnl"] == pytest.approx(10000.00)

            await p.execute_trade("NVDA", 100, 180.00, "SELL", decision_id="dec-3", skip_alpaca_mirror=True)
            assert mock_db.recorded_trades[-1]["realized_pnl"] == pytest.approx(8000.00)

            assert "NVDA" not in p.positions
            assert sum(t["realized_pnl"] for t in mock_db.recorded_trades) == 23000


class TestComplexScenarios:
    """Tests for complex P&L scenarios with mixed BUY/SELL transactions."""

    @pytest.mark.asyncio
    async def test_buy_sell_buy_sequence(self):
        """Test average cost basis through BUY-SELL-BUY sequence."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 100000.00
        p.positions = {}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            await p.execute_trade("AMD", 1000, 50.00, "BUY", decision_id="dec-1", skip_alpaca_mirror=True)
            assert p.positions["AMD"].average_cost_basis == 50.00

            await p.execute_trade("AMD", 500, 80.00, "SELL", decision_id="dec-2", skip_alpaca_mirror=True)
            assert p.positions["AMD"].quantity == 500
            assert p.positions["AMD"].average_cost_basis == 50.00

            await p.execute_trade("AMD", 1000, 90.00, "BUY", decision_id="dec-3", skip_alpaca_mirror=True)
            assert p.positions["AMD"].quantity == 1500
            assert p.positions["AMD"].average_cost_basis == pytest.approx(76.67, abs=0.01)

    @pytest.mark.asyncio
    async def test_multi_part_buy_sell_sequence(self):
        """Test a complex sequence of multiple buys and sells."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 100000.00
        p.positions = {}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            await p.execute_trade("NVDA", 100, 100.00, "BUY", decision_id="dec-1", skip_alpaca_mirror=True)
            assert p.positions["NVDA"].average_cost_basis == 100.00

            await p.execute_trade("NVDA", 100, 120.00, "BUY", decision_id="dec-2", skip_alpaca_mirror=True)
            assert p.positions["NVDA"].quantity == 200
            assert p.positions["NVDA"].average_cost_basis == 110.00

            await p.execute_trade("NVDA", 50, 130.00, "SELL", decision_id="dec-3", skip_alpaca_mirror=True)
            assert mock_db.recorded_trades[-1]["realized_pnl"] == 1000.00
            assert p.positions["NVDA"].quantity == 150
            assert p.positions["NVDA"].average_cost_basis == 110.00

            await p.execute_trade("NVDA", 50, 150.00, "BUY", decision_id="dec-4", skip_alpaca_mirror=True)
            assert p.positions["NVDA"].quantity == 200
            assert p.positions["NVDA"].average_cost_basis == 120.00

            await p.execute_trade("NVDA", 20, 160.00, "SELL", decision_id="dec-5", skip_alpaca_mirror=True)
            assert mock_db.recorded_trades[-1]["realized_pnl"] == 800.00
            assert p.positions["NVDA"].quantity == 180
            assert p.positions["NVDA"].average_cost_basis == 120.00

    @pytest.mark.asyncio
    async def test_sell_without_position_returns_none(self):
        """Test that SELL without position returns None and doesn't record P&L."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 10000.00
        p.positions = {}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            result = await p.execute_trade("AAPL", 100, 150.00, "SELL", decision_id="dec-1", skip_alpaca_mirror=True)
            assert result is None
            mock_db.rpc.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_cost_basis_edge_case(self):
        """Test P&L calculation when cost basis is zero (edge case)."""
        p = Portfolio("test_agent")
        p.id = "test-portfolio-1"
        p.cash_balance = 10000.00
        p.positions = {"GRNT": Position(ticker="GRNT", quantity=100, average_cost_basis=0.00)}
        mock_db = _make_rpc_db(p)

        with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
            await p.execute_trade("GRNT", 100, 50.00, "SELL", decision_id="dec-1", skip_alpaca_mirror=True)
            trade_data = mock_db.recorded_trades[-1]
            assert trade_data["realized_pnl"] == 5000.00
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
            "MSFT": Position(ticker="MSFT", quantity=50, average_cost_basis=300.00),
        }

        current_prices = {
            "AAPL": 175.00,
            "MSFT": 280.00,
        }

        summary = await p.get_portfolio_summary(current_prices)

        assert "AAPL" in summary
        assert "P/L:" in summary
        assert "2500.00" in summary or "2,500.00" in summary or "+2,500" in summary or "+2500" in summary

        assert "MSFT" in summary
        assert "-1000.00" in summary or "-1,000.00" in summary or "-1000" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
