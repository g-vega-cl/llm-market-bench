from unittest.mock import MagicMock, patch

import pytest

from execution.portfolio import Portfolio, Position


@pytest.mark.asyncio
async def test_execute_trade_price_persistence():
    """Verify that execute_trade passes ALL position prices to metrics calculation."""
    owner_id = "test_owner"
    portfolio = Portfolio(owner_id)

    # Mock portfolio ID and positions
    portfolio.id = "test-uuid"
    portfolio.positions = {
        "AAPL": Position(ticker="AAPL", quantity=10, average_cost_basis=150.0),
        "MSFT": Position(ticker="MSFT", quantity=5, average_cost_basis=300.0),
    }
    portfolio.cash_balance = 10000.0

    # Mock Supabase
    mock_supabase = MagicMock()
    # Mock the various table calls to avoid DB errors
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-id"}])
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-id"}])
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    with (
        patch("execution.portfolio.get_supabase_client", return_value=mock_supabase),
        patch.object(portfolio, "calculate_reg_t_metrics") as mock_calc,
        patch.object(portfolio, "save_metrics"),
    ):
        # Execute a sell trade for AAPL
        await portfolio.execute_trade(ticker="AAPL", quantity=2, price=160.0, signal="SELL")

        # Verify calculate_reg_t_metrics was called with both AAPL and MSFT prices
        # MSFT price should be its cost basis (300.0)
        # AAPL price should be the execution price (160.0)
        mock_calc.assert_called_once()
        called_prices = mock_calc.call_args[0][0]

        assert "AAPL" in called_prices
        assert "MSFT" in called_prices
        assert called_prices["AAPL"] == 160.0
        assert called_prices["MSFT"] == 300.0
