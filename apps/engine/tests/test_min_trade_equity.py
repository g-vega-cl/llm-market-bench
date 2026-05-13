"""Tests for minimum trade size - equity-based (not buying power based)."""

from execution.reg_t_validation import RegTMetrics, validate_trade_compliance


def test_min_trade_uses_equity_not_buying_power():
    """Test that minimum trade is 10% of equity, not max(equity, buying power).
    
    Scenario:
    - Cash: $10,000
    - Buying Power: $40,000 (includes margin)
    - Total Equity: $10,000
    
    With old logic: min = max($1000, 0.10 * 40000) = $4,000
    With new logic: min = max($1000, 0.10 * 10000) = $1,000
    """
    # Create metrics with $40k buying power but only $10k equity
    metrics = RegTMetrics(
        total_equity=10000.0,
        initial_margin_req=0.0,
        maintenance_margin_req=0.0,
        available_funds=10000.0,
        excess_liquidity=10000.0,
        sma=10000.0,
        realized=10000.0,
        buying_power=40000.0
    )
    
    # Test a $1,200 trade (should pass with equity-based logic since $1,200 > $1,000)
    # but would fail with buying-power-based logic since $1,200 < $4,000
    result = validate_trade_compliance(
        portfolio_metrics=metrics,
        estimated_trade_cost=1200.0,  # $1,200 for 5 shares @ $240
        ticker="AAPL",
        price=240.0,
        signal="BUY",
        is_sell_tool_used=False
    )
    
    # Should PASS because $1,200 >= $1,000 (10% of equity)
    assert result.passed, f"Expected valid but got: {result.reason}"
    assert result.reason is None or "below dynamic minimum" not in result.reason


def test_min_trade_still_enforces_floor():
    """Test that the $1,000 absolute floor is still enforced.
    
    Even if 10% of equity is less than $1,000, the $1,000 floor applies.
    """
    # Small account: $5k equity
    metrics = RegTMetrics(
        total_equity=5000.0,
        initial_margin_req=0.0,
        maintenance_margin_req=0.0,
        available_funds=5000.0,
        excess_liquidity=5000.0,
        sma=5000.0,
        realized=5000.0,
        buying_power=10000.0
    )
    
    # Test a $500 trade (below $1,000 floor)
    result = validate_trade_compliance(
        portfolio_metrics=metrics,
        estimated_trade_cost=500.0,
        ticker="SPY",
        price=500.0,
        signal="BUY",
        is_sell_tool_used=False
    )
    
    # Should FAIL - below $1,000 floor
    assert not result.passed
    assert "minimum" in result.reason.lower()


def test_min_trade_with_higher_equity():
    """Test that 10% of equity is correctly calculated when equity > $1,000.
    
    Scenario:
    - Cash: $20,000
    - Buying Power: $80,000 (margin)
    - Total Equity: $20,000
    
    Expected min = max($1000, 0.10 * 20000) = $2,000
    """
    metrics = RegTMetrics(
        total_equity=20000.0,
        initial_margin_req=0.0,
        maintenance_margin_req=0.0,
        available_funds=20000.0,
        excess_liquidity=20000.0,
        sma=20000.0,
        realized=20000.0,
        buying_power=80000.0
    )
    
    # Test a $1,500 trade - should fail ($1,500 < $2,000)
    result = validate_trade_compliance(
        portfolio_metrics=metrics,
        estimated_trade_cost=1500.0,
        ticker="NVDA",
        price=150.0,
        signal="BUY",
        is_sell_tool_used=False
    )
    
    assert not result.passed
    
    # Test a $2,500 trade - should pass ($2,500 >= $2,000)
    result = validate_trade_compliance(
        portfolio_metrics=metrics,
        estimated_trade_cost=2550.0,  # 17 shares * $150
        ticker="NVDA",
        price=150.0,
        signal="BUY",
        is_sell_tool_used=False
    )
    
    # $2,550 >= $2,000 (10% of equity) = PASS
    assert result.passed, f"Expected valid but got: {result.reason}"


if __name__ == "__main__":
    test_min_trade_uses_equity_not_buying_power()
    test_min_trade_still_enforces_floor()
    test_min_trade_with_higher_equity()