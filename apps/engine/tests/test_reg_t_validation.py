"""Tests for Cash-Only Account Validation (Formerly Reg-T Margin Scenarios)."""

import pytest

from execution.reg_t_validation import (
    calculate_reg_t_metrics,
    validate_trade_compliance,
)


def test_scenario_1_near_full_cash_no_leverage():
    """Scenario 1: Near-Full Cash Allocation (No Leverage).

    Buying $9,950.24 stock with $10,000 cash.
    """
    cash = 49.76
    positions = {"QQQ": {"quantity": 16, "average_cost_basis": 621.89}}
    prices = {"QQQ": 621.89}

    metrics = calculate_reg_t_metrics(cash, positions, prices, previous_sma=4328.36)

    assert metrics.total_equity == pytest.approx(10000.00, abs=0.1)
    assert metrics.initial_margin_req == 0.0
    assert metrics.maintenance_margin_req == 0.0
    assert metrics.available_funds == pytest.approx(49.76, abs=0.1)
    # Buying power strictly equals available cash
    assert metrics.buying_power == pytest.approx(49.76, abs=0.1)
    assert metrics.sma == pytest.approx(49.76, abs=0.1)
    assert metrics.realized == pytest.approx(10000.00, abs=0.1)


def test_scenario_2_profitable_leveraged():
    """Scenario 2: Negative Cash Boundary (Overdraft / Legacy Deficit).

    In cash-only model, negative cash yields zero buying power and zero margin requirements.
    """
    cash = -2000.00
    positions = {"QQQ": {"quantity": 20, "average_cost_basis": 600.00}}
    prices = {"QQQ": 621.89}

    metrics = calculate_reg_t_metrics(cash, positions, prices)

    assert metrics.total_equity == pytest.approx(10437.80, abs=0.1)
    assert metrics.initial_margin_req == 0.0
    assert metrics.maintenance_margin_req == 0.0
    assert metrics.sma == 0.0
    assert metrics.realized == pytest.approx(10000.00, abs=0.1)
    assert metrics.buying_power == 0.0


def test_scenario_3_loss_leveraged():
    """Scenario 3: Negative Cash Deficit at a Loss.

    In cash-only model, negative cash yields zero buying power.
    """
    cash = -3000.00
    positions = {"QQQ": {"quantity": 20, "average_cost_basis": 650.0}}
    prices = {"QQQ": 621.89}

    metrics = calculate_reg_t_metrics(cash, positions, prices)

    assert metrics.total_equity == pytest.approx(9437.80, abs=0.1)
    assert metrics.initial_margin_req == 0.0
    assert metrics.maintenance_margin_req == 0.0
    assert metrics.sma == 0.0
    assert metrics.realized == pytest.approx(10000.00, abs=0.1)
    assert metrics.buying_power == 0.0


def test_scenario_5_high_leverage():
    """Scenario 5: High Deficit / Overdraft Boundary.

    Cash: -28,000. Stock: 38,000.
    """
    cash = -28000.00
    positions = {"QQQ": {"quantity": 1}}
    prices = {"QQQ": 38000.00}

    metrics = calculate_reg_t_metrics(cash, positions, prices)

    assert metrics.total_equity == pytest.approx(10000.00, abs=0.1)
    assert metrics.initial_margin_req == 0.0
    assert metrics.available_funds == 0.0
    assert metrics.sma == 0.0
    assert metrics.buying_power == 0.0


def test_trade_validation_logic():
    """Explicit tests for Trade Acceptance/Rejection based on Cash Balance Buying Power."""
    cash = 10000.00
    positions = {}
    prices = {}
    metrics = calculate_reg_t_metrics(cash, positions, prices)

    # In cash-only, BP == Cash Balance ($10,000)
    assert metrics.buying_power == 10000.00

    # Case 1: PASS - Buy within cash balance ($5,000 <= $10,000)
    res_pass = validate_trade_compliance(metrics, 5000.00, "AAPL", 150.00)
    assert res_pass.passed is True
    assert res_pass.reason is None

    # Case 2: FAIL - Exceeds Cash Balance Buying Power ($15,000 > $10,000)
    res_fail = validate_trade_compliance(metrics, 15000.00, "AAPL", 150.00)
    assert res_fail.passed is False
    assert "Insufficient" in res_fail.reason
    assert "Available Cash: $10,000.00" in res_fail.reason

    # Case 3: FAIL - Zero BP (deficit state)
    metrics_liquid = calculate_reg_t_metrics(
        cash_balance=-28000.0, positions={"QQQ": {"quantity": 1}}, current_prices={"QQQ": 38000.0}
    )
    assert metrics_liquid.buying_power == 0.0

    res_liquid = validate_trade_compliance(metrics_liquid, 100.00, "QQQ", 38000.0)
    assert res_liquid.passed is False
    assert "Insufficient" in res_liquid.reason
    assert "Available Cash: $0.00" in res_liquid.reason


def test_calculate_reg_t_metrics_with_object_positions():
    """Verify that calculate_reg_t_metrics correctly handles objects with .quantity."""

    class MockPosition:
        def __init__(self, qty):
            self.quantity = qty

    cash = 1000.0
    positions = {"AAPL": MockPosition(10), "MSFT": {"quantity": 5}}
    prices = {
        "AAPL": 150.0,  # 1500
        "MSFT": 300.0,  # 1500
    }

    metrics = calculate_reg_t_metrics(cash, positions, prices)

    assert metrics.total_equity == 4000.0
    assert metrics.maintenance_margin_req == 0.0
    assert metrics.initial_margin_req == 0.0
    assert metrics.available_funds == 1000.0
    assert metrics.buying_power == 1000.0


def test_cash_only_clean_trade_sizing():
    """Verify that trades up to available cash pass without obsolete SMA penalties."""
    cash = 10000.00
    metrics = calculate_reg_t_metrics(cash, {}, {})

    # Buy $9,000 of AAPL (90% of cash). Under old SMA rules, projected SMA = 10k - 9k*0.57 = 4870 >= 1000.
    res_pass = validate_trade_compliance(metrics, 9000.00, "AAPL", 150.00)
    assert res_pass.passed is True

    # Buy $10,001 of AAPL (exceeds cash by $1)
    res_fail = validate_trade_compliance(metrics, 10001.00, "AAPL", 150.00)
    assert res_fail.passed is False
    assert "Insufficient" in res_fail.reason


def test_dynamic_buy_minimum_validation():
    """Verify that BUY trades below 10% of Equity are rejected.

    With $10,000 equity, 10% = $1,000. The minimum is max($1,000, 10% of equity) = $1,000.
    """
    cash = 10000.00
    metrics = calculate_reg_t_metrics(cash, {}, {})

    assert metrics.total_equity == 10000.00
    assert metrics.buying_power == 10000.00

    # CASE 1: PASS - Trade above $1,000
    res_pass = validate_trade_compliance(metrics, 3500.00, "AAPL", 150.00)
    assert res_pass.passed is True

    # CASE 2: PASS - Trade at minimum $1,000
    res_pass_min = validate_trade_compliance(metrics, 1000.00, "AAPL", 150.00)
    assert res_pass_min.passed is True

    # CASE 3: FAIL - Trade below $1,000 (absolute floor)
    res_fail = validate_trade_compliance(metrics, 500.00, "AAPL", 150.00)
    assert res_fail.passed is False
    assert "minimum threshold" in res_fail.reason
    assert "$1,000.00" in res_fail.reason
