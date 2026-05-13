"""Verification test for negative total equity fix.

This test simulates a market data failure (price = 0) for a position on margin
and verifies that the system falls back to cost basis to prevent negative equity.
"""

from execution.portfolio import Portfolio, Position


def test_negative_equity_fix_fallback():
    # Setup: Account on margin
    # Cash: -3000. Holds 10 shares of GLD @ 400 (Cost Basis: 4000)
    # Total Equity (at cost): 4000 - 3000 = 1000.
    
    p = Portfolio("test_agent")
    p.cash_balance = -3000.0
    p.positions = {"GLD": Position("GLD", 10, 400.0)}
    
    # CASE 1: Market data fails (price missing or 0)
    current_prices = {"GLD": 0.0}
    
    metrics = p.calculate_reg_t_metrics(current_prices)
    
    # Verification: Total equity should be calculated using cost basis (400)
    # stock_value = 10 * 400 = 4000
    # total_equity = 4000 - 3000 = 1000
    
    assert metrics.total_equity == 1000.0
    assert metrics.total_equity > 0, "Equity should be positive using cost basis fallback"
    print(f"\n[PASS] Total Equity fallback: {metrics.total_equity}")

def test_negative_equity_fix_no_fallback_needed():
    # CASE 2: Market data is available
    p = Portfolio("test_agent")
    p.cash_balance = -3000.0
    p.positions = {"GLD": Position("GLD", 10, 400.0)}
    
    current_prices = {"GLD": 450.0}
    metrics = p.calculate_reg_t_metrics(current_prices)
    
    # stock_value = 10 * 450 = 4500
    # total_equity = 4500 - 3000 = 1500
    assert metrics.total_equity == 1500.0
    print(f"[PASS] Total Equity with market price: {metrics.total_equity}")

if __name__ == "__main__":
    test_negative_equity_fix_fallback()
    test_negative_equity_fix_no_fallback_needed()
