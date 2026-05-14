"""Tests for Regulation T margin logic - Full Scenario Suite."""
import pytest

from execution.reg_t_validation import (
    calculate_reg_t_metrics,
    validate_trade_compliance,
)

# Reference: raw/docs/engine/account-buying-power-reg-t4-calculations.md

def test_scenario_1_near_full_cash_no_leverage():
    """Scenario 1: Near-Full Cash Allocation (No Leverage).
    
    Buying $9,950.24 stock with $10,000 cash.
    """
    cash = 49.76
    positions = {"QQQ": {"quantity": 16, "average_cost_basis": 621.89}} 
    prices = {"QQQ": 621.89}
    # If we started with 10k, bought 9950, SMA drops by 4975 (50%).
    # New SMA = 5025.
    # Metrics Calc logic: Ratchet.
    # Equity = 10000. IM = 4975.12. Surplus = 5024.88.
    # Max(Prev, Surplus) depends on what Prev is passed.
    # In this test, we verify that the CALCULATED surplus is correct.
    # If we assume previous_sma was correctly updated to 5024.88 by the trade.
    
    metrics = calculate_reg_t_metrics(cash, positions, prices, previous_sma=4328.36)
    
    assert metrics.total_equity == pytest.approx(10000.00, abs=0.1)
    assert metrics.initial_margin_req == pytest.approx(5671.64, abs=0.1)
    assert metrics.maintenance_margin_req == pytest.approx(3283.58, abs=0.1)
    # Available Funds = 10000 - 5671.64 = 4328.36
    assert metrics.available_funds == pytest.approx(4328.36, abs=0.1)
    # BP = 4 * Avail Funds = 17313.44
    assert metrics.buying_power == pytest.approx(17313.44, abs=1.0)
    # SMA should match Available Funds here since no gains to ratchet it higher
    assert metrics.sma == pytest.approx(4328.36, abs=0.1)
    # Realized = 49.76 + 9950.24 = 10000.00
    assert metrics.realized == pytest.approx(10000.00, abs=0.1)


def test_scenario_2_profitable_leveraged():
    """Scenario 2: Profitable Leveraged Position.
    
    Bought $12k stock (borrowed 2k). Stock passed from 600 to 621.89.
    Current Cash: -2000.
    Current Stock: 12,437.80.
    """
    cash = -2000.00
    positions = {"QQQ": {"quantity": 20, "average_cost_basis": 600.00}} 
    prices = {"QQQ": 621.89}
    
    # Previous SMA Calculation:
    # Start 10k. Buy 12k (Cost). SMA -= 57% of 12k (6840). Prev SMA = 3160.
    previous_sma = 3160.00 
    
    metrics = calculate_reg_t_metrics(cash, positions, prices, previous_sma=previous_sma)
    
    assert metrics.total_equity == pytest.approx(10437.80, abs=0.1)
    # IM = 12437.80 * 0.57 = 7089.55
    assert metrics.initial_margin_req == pytest.approx(7089.55, abs=0.1)
    # Surplus = Eq - IM = 10437.8 - 7089.55 = 3348.25
    # SMA Ratchet: Max(3160, 3348.25) -> 3348.25
    assert metrics.sma == pytest.approx(3348.25, abs=0.1)
    
    # Realized = -2000 + 12000 (Cost basis) = 10000.00
    # Note: Scenario 2 bought $12k stock.
    assert metrics.realized == pytest.approx(10000.00, abs=0.1)
    
    # BP = 4 * Available Funds (3348.25) = 13393.00
    assert metrics.buying_power == pytest.approx(13393.00, abs=1.0)


def test_scenario_3_loss_leveraged():
    """Scenario 3: Leveraged Position at a Loss.
    
    Bought 13k stock (borrowed 3k). Dropped from 650 to 621.89.
    Cash: -3000.
    Stock: 12,437.80.
    """
    cash = -3000.00
    positions = {"QQQ": {"quantity": 20, "average_cost_basis": 650.0} } 
    prices = {"QQQ": 621.89}
    
    # Previous SMA logic:
    # Start 10k. Buy 12k. SMA -= 6840. Prev SMA = 3160.
    previous_sma = 3160.00
    
    metrics = calculate_reg_t_metrics(cash, positions, prices, previous_sma=previous_sma)
    
    assert metrics.total_equity == pytest.approx(9437.80, abs=0.1)
    # IM = 7089.55 (57% of market value)
    # Surplus = Eq - IM = 9437.80 - 7089.55 = 2348.25.
    
    # RATCHET LOGIC TEST:
    # Surplus (2348.25) < Previous SMA (3160).
    # SMA should HOLD at 3160.
    assert metrics.sma == pytest.approx(3160.00, abs=0.1)

    # Realized = -3000 + 13000 (Cost basis) = 10000.00
    assert metrics.realized == pytest.approx(10000.00, abs=0.1)
    
    # BP is based on Available Funds (Surplus) = 2348.25 * 4 = 9393.00.
    # Note: BP uses current reality (Surplus), not the SMA historic high.
    assert metrics.buying_power == pytest.approx(9393.00, abs=1.0)


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
    assert metrics.initial_margin_req == pytest.approx(21660.00, abs=0.1)
    
    # Available Funds = 10k - 21660 = -11660.
    assert metrics.available_funds == pytest.approx(-11660.00, abs=0.1)
    
    # SMA should be 0 (Max(0, -11660))
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
    assert "Available BP: $0.00" in res_liquid.reason


def test_calculate_reg_t_metrics_with_object_positions():
    """Verify that calculate_reg_t_metrics correctly handles objects with .quantity."""
    class MockPosition:
        def __init__(self, qty):
            self.quantity = qty

    cash = 1000.0
    # Mix of dict and object access
    positions = {
        "AAPL": MockPosition(10),
        "MSFT": {"quantity": 5}
    }
    prices = {
        "AAPL": 150.0, # 1500
        "MSFT": 300.0  # 1500
    }
    # Total Value: 3000
    # Equity: 4000
    # MM (25%): 750
    # IM (50%): 1500
    
    metrics = calculate_reg_t_metrics(cash, positions, prices)
    
    assert metrics.total_equity == 4000.0
    assert metrics.maintenance_margin_req == 3000.0 * 0.33
    assert metrics.initial_margin_req == 3000.0 * 0.57
    assert metrics.available_funds == 4000.0 - (3000.0 * 0.57)


def test_sma_floor_protection():
    """Verify that trades are rejected if projected SMA < 10% of total equity."""
    # Setup: $10,000 Fresh Account
    cash = 10000.00
    positions = {}
    prices = {}
    previous_sma = 10000.00
    
    metrics = calculate_reg_t_metrics(cash, positions, prices, previous_sma=previous_sma)
    
    # 1. Test a large buy that hits the SMA floor
    # Cost = $16,000. 
    # Current SMA = $10,000. 
    # Projected SMA = 10,000 - (16,000 * 0.57) = 10,000 - 9,120 = 880.
    # Floor: 10% of $10,000 = $1,000.
    # Result: Violation (880 < 1000)
    res_violation = validate_trade_compliance(metrics, 16000.00, "AAPL", 150.00)
    assert res_violation.passed is False
    assert "SMA Floor Violation" in res_violation.reason
    assert "Projected SMA: $880.00" in res_violation.reason
    assert "Required Floor (10% Equity): $1,000.00" in res_violation.reason
    
    # 2. Test a slightly smaller buy that stays above the floor
    # Cost = $15,000.
    # Projected SMA = 10,000 - (15,000 * 0.57) = 10,000 - 8,550 = 1,450.
    # Result: PASS (1450 >= 1000)
    res_pass = validate_trade_compliance(metrics, 15000.00, "AAPL", 150.00)
    assert res_pass.passed is True
    
    # 3. Verify max_affordable_shares calculation when floor is hit
    # Max Affordable = (Current SMA - Floor) / (Price * 0.57)
    # (10000 - 1000) / (150 * 0.57) = 9000 / 85.5 = 105.26
    # Should be 105 shares.
    assert res_violation.max_affordable_shares == 105

def test_dynamic_buy_minimum_validation():
    """Verify that BUY trades below 10% of Equity are rejected.
    
    Note: Changed from max(BP, Equity) to Equity-only per user request.
    With $10,000 equity, 10% = $1,000. The minimum is max($1,000, 10% of equity) = $1,000.
    """
    # Setup: $10,000 Equity, $40,000 Buying Power
    cash = 10000.00
    metrics = calculate_reg_t_metrics(cash, {}, {})
    
    assert metrics.total_equity == 10000.00
    assert metrics.buying_power == 40000.00
    
    # 10% of equity ($10,000) is $1,000.
    # Minimum = max($1,000, $1,000) = $1,000
    
    # CASE 1: PASS - Trade above $1,000 (was FAIL with old logic: $3,500 < $4,000)
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
