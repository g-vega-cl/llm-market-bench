"""Tests for Regulation T margin logic - Full Scenario Suite."""
import pytest
from execution.reg_t_validation import (
    calculate_reg_t_metrics, 
    validate_trade_compliance, 
    RegTMetrics
)

# Reference: docs/account-buying-power-reg-t4-calculations.md

def test_scenario_1_near_full_cash_no_leverage():
    """Scenario 1: Near-Full Cash Allocation (No Leverage).
    
    Buying $9,950.24 stock with $10,000 cash.
    """
    cash = 49.76
    positions = {"QQQ": {"quantity": 16}} # 16 * 621.89 = 9950.24
    prices = {"QQQ": 621.89}
    previous_sma = 10000.00 # Started with 10k? Or does it adjust? 
    # If we started with 10k, bought 9950, SMA drops by 4975 (50%).
    # New SMA = 5025.
    # Metrics Calc logic: Ratchet.
    # Equity = 10000. IM = 4975.12. Surplus = 5024.88.
    # Max(Prev, Surplus) depends on what Prev is passed.
    # In this test, we verify that the CALCULATED surplus is correct.
    # If we assume previous_sma was correctly updated to 5024.88 by the trade.
    
    metrics = calculate_reg_t_metrics(cash, positions, prices, previous_sma=5024.88)
    
    assert metrics.total_equity == pytest.approx(10000.00, abs=0.1)
    assert metrics.initial_margin_req == pytest.approx(4975.12, abs=0.1)
    assert metrics.maintenance_margin_req == pytest.approx(2487.56, abs=0.1)
    # Available Funds = 10000 - 4975.12 = 5024.88
    assert metrics.available_funds == pytest.approx(5024.88, abs=0.1)
    # BP = 4 * Avail Funds = 20099.52
    assert metrics.buying_power == pytest.approx(20099.52, abs=1.0)
    # SMA should match Available Funds here since no gains to ratchet it higher
    assert metrics.sma == pytest.approx(5024.88, abs=0.1)


def test_scenario_2_profitable_leveraged():
    """Scenario 2: Profitable Leveraged Position.
    
    Bought $12k stock (borrowed 2k). Stock passed from 600 to 621.89.
    Current Cash: -2000.
    Current Stock: 12,437.80.
    """
    cash = -2000.00
    positions = {"QQQ": {"quantity": 20}} # 20 * 621.89 = 12437.80
    prices = {"QQQ": 621.89}
    
    # Previous SMA Calculation:
    # Start 10k. Buy 12k (Cost). SMA -= 6k. Prev SMA = 4000.
    previous_sma = 4000.00 
    
    metrics = calculate_reg_t_metrics(cash, positions, prices, previous_sma=previous_sma)
    
    assert metrics.total_equity == pytest.approx(10437.80, abs=0.1)
    # IM = 6218.90
    assert metrics.initial_margin_req == pytest.approx(6218.90, abs=0.1)
    # Surplus = Eq - IM = 10437.8 - 6218.9 = 4218.90
    # SMA Ratchet: Max(4000, 4218.90) -> 4218.90
    assert metrics.sma == pytest.approx(4218.90, abs=0.1)
    
    # BP = 4 * Available Funds (4218.90) = 16875.60
    assert metrics.buying_power == pytest.approx(16875.60, abs=1.0)


def test_scenario_3_loss_leveraged():
    """Scenario 3: Leveraged Position at a Loss.
    
    Bought 13k stock (borrowed 3k). Dropped from 650 to 621.89.
    Cash: -3000.
    Stock: 12,437.80.
    """
    cash = -3000.00
    positions = {"QQQ": {"quantity": 20}} 
    prices = {"QQQ": 621.89}
    
    # Previous SMA logic:
    # Start 10k. Buy 13k. SMA -= 6500. Prev SMA = 3500.
    previous_sma = 3500.00
    
    metrics = calculate_reg_t_metrics(cash, positions, prices, previous_sma=previous_sma)
    
    assert metrics.total_equity == pytest.approx(9437.80, abs=0.1)
    # IM = 6218.90 (50% of market value)
    # Surplus = Eq - IM = 9437.80 - 6218.90 = 3218.90.
    
    # RATCHET LOGIC TEST:
    # Surplus (3218) < Previous SMA (3500).
    # SMA should HOLD at 3500.
    assert metrics.sma == pytest.approx(3500.00, abs=0.1)
    
    # BP is based on Available Funds (Surplus) = 3218.90 * 4 = 12875.60.
    # Note: BP uses current reality (Surplus), not the SMA historic high.
    assert metrics.buying_power == pytest.approx(12875.60, abs=1.0)


def test_scenario_5_high_leverage():
    """Scenario 5: High Leverage / Boundary.
    
    Buy 38k stock with 10k cash.
    Cash: -28,000.
    Stock: 38,000.
    """
    cash = -28000.00
    positions = {"QQQ": {"quantity": 1}} # Mocking full value as 1 unit for simplicity
    prices = {"QQQ": 38000.00}
    
    # Prev SMA:
    # Start 10k. Buy 38k. SMA -= 19k. Result -9k? 
    # Doc says excess is 500, available -9000. SMA 0.
    # Let's assume floor at 0.
    previous_sma = 0.00
    
    metrics = calculate_reg_t_metrics(cash, positions, prices, previous_sma=previous_sma)
    
    assert metrics.total_equity == pytest.approx(10000.00, abs=0.1)
    assert metrics.initial_margin_req == pytest.approx(19000.00, abs=0.1)
    
    # Available Funds = 10k - 19k = -9000.
    assert metrics.available_funds == pytest.approx(-9000.00, abs=0.1)
    
    # SMA should be 0 (Max(0, -9000))
    assert metrics.sma == 0.0
    
    # BP should be 0
    assert metrics.buying_power == 0.0


def test_trade_validation_logic():
    """Explicit tests for Trade Acceptance/Rejection based on Buying Power."""
    
    # Setup: Standard $10k Account (Scenario 1 Baseline)
    # Cash 10k. No pos. 
    # Equity 10k. IM 0. Avail 10k. BP 40k? 
    # Wait, S1 in doc has 16 shares.
    # Let's use a FRESH 10k account logic.
    cash = 10000.00
    positions = {}
    prices = {}
    metrics = calculate_reg_t_metrics(cash, positions, prices)
    
    # Equity: 10k. IM: 0. Avail: 10k. BP: 40k.
    assert metrics.buying_power == 40000.00
    
    # Case 1: PASS - Leveraged Buy within limits
    # Buy $15,000 AAPL (Requires borrowing 5k).
    # Cost (15k) < BP (40k).
    res_pass = validate_trade_compliance(metrics, 15000.00, "AAPL", 150.00)
    assert res_pass.passed is True
    assert res_pass.reason is None
    
    # Case 2: FAIL - Exceeds Buying Power
    # Buy $50,000 AAPL.
    # Cost (50k) > BP (40k).
    res_fail = validate_trade_compliance(metrics, 50000.00, "AAPL", 150.00)
    assert res_fail.passed is False
    assert "Insufficient Buying Power" in res_fail.reason
    assert "Available BP: $40,000.00" in res_fail.reason
    
    # Case 3: FAIL - Liquidation State (Scenario 5)
    # Re-create Scenario 5 metrics (Start with bad state)
    metrics_liquid = calculate_reg_t_metrics(
        cash_balance=-28000.0,
        positions={"QQQ": {"quantity": 1}},
        current_prices={"QQQ": 38000.0},
        previous_sma=0.0
    )
    # BP is 0.0 (See test_scenario_5_high_leverage)
    assert metrics_liquid.buying_power == 0.0
    
    # Attempt even a small buy ($100)
    res_liquid = validate_trade_compliance(metrics_liquid, 100.00, "QQQ", 38000.0)
    assert res_liquid.passed is False
    assert "Insufficient Buying Power" in res_liquid.reason
