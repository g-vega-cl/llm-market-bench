"""TDD tests for Cash-Only Portfolio Execution (No Margin)."""

import pytest

from execution.portfolio import Portfolio
from execution.reg_t_validation import (
    calculate_reg_t_metrics,
    validate_trade_compliance,
)


def test_cash_only_metrics_buying_power_equals_cash():
    """Verify buying power strictly equals cash balance with zero leverage."""
    cash = 5000.00
    positions = {"QQQ": {"quantity": 10, "average_cost_basis": 500.00}}
    prices = {"QQQ": 500.00}

    metrics = calculate_reg_t_metrics(cash, positions, prices)

    # Total equity = $5,000 cash + $5,000 stock = $10,000
    assert metrics.total_equity == pytest.approx(10000.00)
    # Buying power must equal cash balance, not 4x or 2x
    assert metrics.buying_power == pytest.approx(5000.00)
    assert metrics.available_funds == pytest.approx(5000.00)
    assert metrics.initial_margin_req == 0.0
    assert metrics.maintenance_margin_req == 0.0
    assert metrics.sma == pytest.approx(5000.00)


def test_cash_only_buy_rejected_when_exceeding_cash():
    """Verify BUY order is rejected when trade cost exceeds available cash balance."""
    cash = 4000.00
    positions = {"AAPL": {"quantity": 30, "average_cost_basis": 200.00}}
    prices = {"AAPL": 200.00}

    metrics = calculate_reg_t_metrics(cash, positions, prices)
    assert metrics.buying_power == pytest.approx(4000.00)

    # Attempt to buy $6,000 of MSFT ($300 * 20 shares)
    result = validate_trade_compliance(
        portfolio_metrics=metrics,
        estimated_trade_cost=6000.00,
        ticker="MSFT",
        price=300.00,
        signal="BUY",
    )

    assert not result.passed
    assert "Insufficient" in result.reason
    assert result.max_affordable_shares == 13  # 4000 // 300


def test_cash_only_buy_passes_up_to_available_cash_without_sma_penalty():
    """Verify BUY order up to available cash is permitted without SMA floor rejection."""
    cash = 4000.00
    positions = {"AAPL": {"quantity": 30, "average_cost_basis": 200.00}}
    prices = {"AAPL": 200.00}

    metrics = calculate_reg_t_metrics(cash, positions, prices)

    # Buy $3,000 of MSFT ($300 * 10 shares)
    # Under old Reg-T: projected SMA = 4000 - (3000 * 0.57) = 2290.
    # If cash was low, SMA floor would reject it even if cash was sufficient.
    result = validate_trade_compliance(
        portfolio_metrics=metrics,
        estimated_trade_cost=3000.00,
        ticker="MSFT",
        price=300.00,
        signal="BUY",
    )

    assert result.passed


@pytest.mark.asyncio
async def test_portfolio_execute_trade_cash_only_deduction(monkeypatch):
    """Verify execute_trade deducts cash 1:1 and prevents negative cash."""
    portfolio = Portfolio("test-cash-only-agent")
    portfolio.id = "mock-uuid"
    portfolio.cash_balance = 5000.00
    portfolio.positions = {}

    # Mock supabase client
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    monkeypatch.setattr("execution.portfolio.get_supabase_client", lambda: mock_client)

    # Execute BUY for $3,000
    trade_id = await portfolio.execute_trade(
        ticker="SPY",
        quantity=6,
        price=500.00,
        signal="BUY",
        skip_alpaca_mirror=True,
    )

    assert trade_id == "trade-1"
    assert portfolio.cash_balance == pytest.approx(2000.00)
    assert portfolio.sma == pytest.approx(2000.00)

    # Attempt BUY that would cause negative cash ($2,500 > $2,000 cash)
    result = await portfolio.execute_trade(
        ticker="SPY",
        quantity=5,
        price=500.00,
        signal="BUY",
        skip_alpaca_mirror=True,
    )
    assert result is None  # Trade should be rejected
    assert portfolio.cash_balance == pytest.approx(2000.00)  # Cash unchanged
