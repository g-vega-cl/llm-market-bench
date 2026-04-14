"""Tests for the 10% minimum position threshold (automatic dust cleanup).

Note: The 10% threshold rule is AUTOMATIC - there is no LLM tool for this.
The engine automatically sells positions below 10% of portfolio equity during the
Pre-Analysis Dust Cleanup phase (before LLM analysis begins).

See: main.py -> _stage_dust_cleanup() and execution/portfolio.py -> _check_and_sell_dust_positions()

These tests verify the automatic enforcement behavior, not a callable tool.
"""

import pytest
from unittest.mock import MagicMock, patch
from execution.portfolio import Portfolio


@pytest.fixture
def mock_supabase():
    """Setup mock Supabase client for dust cleanup tests."""
    with patch("execution.portfolio.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

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
                "realized": 5000.0
            }
        ]

        positions_data = [
            {"ticker": "AAPL", "quantity": 10, "average_cost_basis": 150.0},
            {"ticker": "XYZ", "quantity": 5, "average_cost_basis": 100.0}
        ]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "portfolios":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = portfolio_data
            elif table_name == "portfolio_positions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = positions_data
            return mock_table

        mock_client.table.side_effect = table_side_effect
        yield mock_client


@pytest.mark.asyncio
async def test_automatic_dust_cleanup_below_threshold(mock_supabase):
    """Verify system automatically sells positions below 10% of equity."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    # Setup: $10,000 equity, 5 shares @ $100 = $500 (below 10% = $1,000)
    portfolio.positions = {
        "AAPL": MagicMock(ticker="AAPL", quantity=5, average_cost_basis=100.0)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    current_prices = {"AAPL": 100.0}

    await portfolio._check_and_sell_dust_positions(current_prices)

    # Position should be automatically liquidated
    assert "AAPL" not in portfolio.positions
    # Cash should increase by sale proceeds
    assert portfolio.cash_balance == 5500.0  # 5000 + (5 * 100)


@pytest.mark.asyncio
async def test_no_cleanup_for_positions_above_threshold(mock_supabase):
    """Verify positions above 10% threshold are not automatically sold."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    # Setup: $10,000 equity, 100 shares @ $150 = $15,000 (above 10% = $1,000)
    portfolio.positions = {
        "AAPL": MagicMock(ticker="AAPL", quantity=100, average_cost_basis=150.0)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    current_prices = {"AAPL": 150.0}
    initial_call_count = len(mock_supabase.table.call_args_list)

    await portfolio._check_and_sell_dust_positions(current_prices)

    # No trades should have been executed
    new_calls = mock_supabase.table.call_args_list[initial_call_count:]
    trade_calls = [c for c in new_calls if len(c[0]) > 0 and c[0][0] == "trades"]
    assert len(trade_calls) == 0
    # Position should still exist
    assert "AAPL" in portfolio.positions


@pytest.mark.asyncio
async def test_handles_zero_quantity_position(mock_supabase):
    """Verify zero quantity positions are ignored."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    portfolio.positions = {
        "DEAD": MagicMock(ticker="DEAD", quantity=0, average_cost_basis=50.0)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    current_prices = {"DEAD": 0.0}
    initial_call_count = len(mock_supabase.table.call_args_list)

    await portfolio._check_and_sell_dust_positions(current_prices)

    new_calls = mock_supabase.table.call_args_list[initial_call_count:]
    trade_calls = [c for c in new_calls if len(c[0]) > 0 and c[0][0] == "trades"]
    assert len(trade_calls) == 0


@pytest.mark.asyncio
async def test_handles_market_data_error_gracefully(mock_supabase):
    """Verify positions with zero/negative value are not sold."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    portfolio.positions = {
        "AAPL": MagicMock(ticker="AAPL", quantity=5, average_cost_basis=100.0)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    # Simulate market data error (price = 0)
    current_prices = {"AAPL": 0.0}
    initial_call_count = len(mock_supabase.table.call_args_list)

    await portfolio._check_and_sell_dust_positions(current_prices)

    # Should not attempt to sell a position with zero value
    new_calls = mock_supabase.table.call_args_list[initial_call_count:]
    trade_calls = [c for c in new_calls if len(c[0]) > 0 and c[0][0] == "trades"]
    assert len(trade_calls) == 0


@pytest.mark.asyncio
async def test_exact_threshold_boundary(mock_supabase):
    """Verify behavior when position is exactly at 10% threshold."""
    portfolio = Portfolio(owner_id="test-agent")
    await portfolio.initialize()

    # 10 shares @ $100 = $1,000 (exactly 10% of $10,000)
    portfolio.positions = {
        "AAPL": MagicMock(ticker="AAPL", quantity=10, average_cost_basis=100.0)
    }
    portfolio.metrics = MagicMock(total_equity=10000.0)
    portfolio.cash_balance = 5000.0
    portfolio.id = "test-portfolio-id"

    current_prices = {"AAPL": 100.0}
    initial_call_count = len(mock_supabase.table.call_args_list)

    await portfolio._check_and_sell_dust_positions(current_prices)

    # Position at exactly 10% should NOT be sold (condition is < threshold, not <=)
    new_calls = mock_supabase.table.call_args_list[initial_call_count:]
    trade_calls = [c for c in new_calls if len(c[0]) > 0 and c[0][0] == "trades"]
    assert len(trade_calls) == 0
    assert "AAPL" in portfolio.positions
