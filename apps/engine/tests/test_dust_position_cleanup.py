"""Tests for the 10% minimum position rule (dust position cleanup)."""

from unittest.mock import MagicMock, patch

import pytest

from execution.portfolio import Portfolio


@pytest.fixture
def mock_supabase():
    """Setup mock Supabase client."""
    with patch("execution.portfolio.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock portfolio fetch
        portfolio_data = [
            {
                "id": "test-portfolio-id",
                "owner_id": "test-agent",
                "cash_balance": 5000.0,
                "sma": 5000.0,
                "total_equity": 10000.0,
                "buying_power": 20000.0,
                "excess_liquidity": 7000.0,
                "maintenance_margin": 3000.0,
                "realized": 5000.0,
            }
        ]

        # Mock positions fetch
        positions_data = [
            {"ticker": "AAPL", "quantity": 10, "average_cost_basis": 150.0},
            {"ticker": "XYZ", "quantity": 5, "average_cost_basis": 100.0},
        ]

        # Use side_effect to return different data based on table name
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "portfolios":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = portfolio_data
            elif table_name == "portfolio_positions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = positions_data
            # For all other tables, the default MagicMock behavior is fine
            return mock_table

        mock_client.table.side_effect = table_side_effect

        rpc_seq = {"n": 0}

        def rpc_side_effect(fn_name, params):
            rpc_seq["n"] += 1
            call_mock = MagicMock()
            qty = int(params["p_quantity"])
            price = float(params["p_price"])
            new_cash = portfolio_data[0]["cash_balance"] + qty * price
            portfolio_data[0]["cash_balance"] = new_cash
            call_mock.execute.return_value = MagicMock(
                data={
                    "trade_id": f"dust-trade-{rpc_seq['n']}",
                    "cash_balance": new_cash,
                    "sma": max(0.0, new_cash),
                    "quantity": qty,
                    "total_cost": qty * price,
                    "position_quantity": 0,
                    "position_avg_cost": 0.0,
                    "idempotent_replay": False,
                }
            )
            return call_mock

        mock_client.rpc.side_effect = rpc_side_effect

        yield mock_client


@pytest.mark.asyncio
async def test_dust_position_cleanup_after_partial_sell(mock_supabase):
    """Verify that positions below 10% of equity are automatically sold after a SELL trade."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    # Setup: Portfolio has $10,000 equity, owns AAPL (3 shares @ $150 = $450) and XYZ (5 shares @ $100 = $500)
    # Both are below 10% threshold ($1,000)
    portfolio.positions = {
        "AAPL": MagicMock(ticker="AAPL", quantity=3, average_cost_basis=150.0),  # $450 value (below 10%)
        "XYZ": MagicMock(ticker="XYZ", quantity=5, average_cost_basis=100.0),  # $500 value (below 10%)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    # Simulate current prices
    current_prices = {"AAPL": 150.0, "XYZ": 100.0}

    # Run dust cleanup
    await portfolio._check_and_sell_dust_positions(current_prices)

    # Verify both dust positions triggered the atomic execute_portfolio_trade RPC
    rpc_calls = [call for call in mock_supabase.rpc.call_args_list if call[0][0] == "execute_portfolio_trade"]
    assert len(rpc_calls) == 2
    sold_tickers = {call[0][1]["p_ticker"] for call in rpc_calls}
    assert sold_tickers == {"AAPL", "XYZ"}


@pytest.mark.asyncio
async def test_no_cleanup_for_positions_above_threshold(mock_supabase):
    """Verify that positions above 10% threshold are not sold."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    # Setup: Portfolio has $10,000 equity, owns large position
    portfolio.positions = {
        "AAPL": MagicMock(ticker="AAPL", quantity=100, average_cost_basis=150.0)  # $15,000 value (above 10%)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    current_prices = {"AAPL": 150.0}

    # Track table calls before running
    initial_call_count = len(mock_supabase.table.call_args_list)

    # Run dust cleanup
    await portfolio._check_and_sell_dust_positions(current_prices)

    # No new table calls for trades or deletes should have been made
    new_calls = mock_supabase.table.call_args_list[initial_call_count:]
    trade_calls = [call for call in new_calls if len(call[0]) > 0 and call[0][0] == "trades"]
    assert len(trade_calls) == 0

    # Position should still exist
    assert "AAPL" in portfolio.positions


@pytest.mark.asyncio
async def test_dust_cleanup_with_zero_value_position(mock_supabase):
    """Verify that positions with zero or negative value are ignored."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    # Setup: Portfolio has a position with zero quantity
    portfolio.positions = {
        "DEAD": MagicMock(ticker="DEAD", quantity=0, average_cost_basis=50.0)  # $0 value
    }
    portfolio.metrics = MagicMock(total_equity=10000.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    current_prices = {"DEAD": 0.0}

    # Track table calls before running
    initial_call_count = len(mock_supabase.table.call_args_list)

    # Run dust cleanup
    await portfolio._check_and_sell_dust_positions(current_prices)

    # No new table calls for trades or deletes should have been made
    new_calls = mock_supabase.table.call_args_list[initial_call_count:]
    trade_calls = [call for call in new_calls if len(call[0]) > 0 and call[0][0] == "trades"]
    assert len(trade_calls) == 0


@pytest.mark.asyncio
async def test_dust_cleanup_updates_portfolio_metrics(mock_supabase):
    """Verify that dust cleanup properly updates portfolio metrics after selling."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    # Setup: Small dust position
    portfolio.positions = {
        "DUST": MagicMock(ticker="DUST", quantity=2, average_cost_basis=100.0)  # $200 value (below 10%)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    current_prices = {"DUST": 100.0}

    # Run dust cleanup
    await portfolio._check_and_sell_dust_positions(current_prices)

    # Position should be removed
    assert "DUST" not in portfolio.positions
    # Cash should increase by sale proceeds ($200)
    assert portfolio.cash_balance == 5200.0


@pytest.mark.asyncio
async def test_dust_cleanup_handles_exceptions_gracefully(mock_supabase):
    """Verify that exceptions during dust cleanup are logged but don't crash."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    # Setup: Position that will cause an error
    portfolio.positions = {"ERROR": MagicMock(ticker="ERROR", quantity=5, average_cost_basis=100.0)}
    portfolio.metrics = MagicMock(total_equity=10000.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    current_prices = {"ERROR": 100.0}

    # Mock RPC to raise an exception
    mock_supabase.rpc.side_effect = RuntimeError("DB Error")

    # Run dust cleanup - should not crash
    await portfolio._check_and_sell_dust_positions(current_prices)

    # Atomic rollback: when RPC fails, local cash and position remain unchanged
    assert portfolio.cash_balance == 5000.0
    assert "ERROR" in portfolio.positions


@pytest.mark.asyncio
async def test_dust_cleanup_recalculates_metrics_with_current_prices(mock_supabase):
    """Verify that after dust cleanup, metrics are calculated using actual current prices
    for the remaining positions rather than their cost basis."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    portfolio.positions = {
        "DUST": MagicMock(ticker="DUST", quantity=2, average_cost_basis=100.0),
        "KEEP": MagicMock(ticker="KEEP", quantity=10, average_cost_basis=100.0),
    }
    portfolio.metrics = MagicMock(total_equity=7200.0, sma=5000.0, buying_power=20000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    current_prices = {"DUST": 100.0, "KEEP": 200.0}

    await portfolio._check_and_sell_dust_positions(current_prices)

    assert "DUST" not in portfolio.positions
    assert "KEEP" in portfolio.positions
    assert portfolio.cash_balance == 5200.0

    # KEEP has quantity=10, current_price=200.0 -> Value = 2000.0
    # Cash = 5200.0
    # Total Equity = 5200.0 + 2000.0 = 7200.0
    # (If the bug is present, KEEP is valued at cost basis $100 -> Value = 1000.0, Total Equity = 6200.0)
    assert portfolio.metrics.total_equity == 7200.0
