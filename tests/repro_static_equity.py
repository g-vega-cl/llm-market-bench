import asyncio
from apps.engine.execution.portfolio import Portfolio, Position
from apps.engine.execution.reg_t_validation import calculate_reg_t_metrics

# Mock the database interaction by overriding the relevant methods or mocking the dependencies
# but for this specific logic test, we can test the calculation function directly 
# or the Portfolio class with mocked DB calls if needed.
# However, the bug is likely in the *interaction* or the *absence* of price data passed to it.

def test_static_equity_bug():
    print("--- Starting Repro: Static Equity Bug ---")

    # 1. Setup a Portfolio State with $10k cash and 1 position
    # Assume we bought 10 shares of NVDA at $1000.
    portfolio_cash = 0.0  # Spent 10k
    quantity = 10
    avg_cost = 1000.0
    
    positions = {
        "NVDA": Position(ticker="NVDA", quantity=quantity, average_cost_basis=avg_cost)
    }
    
    # 2. Case A: Market Data Missing (Price = 0 or missing from map)
    # This simulates the current bug where main.py might be passing an empty map 
    # or the ticker is just missing.
    print("\n[Case A] Testing with MISSING market data (simulating the bug)...")
    price_map_missing = {} 
    
    metrics_run_1 = calculate_reg_t_metrics(
        cash_balance=portfolio_cash,
        positions=positions,
        current_prices=price_map_missing,
        previous_sma=0.0
    )
    
    # Expected Behavior (The Bug): Total Equity = Cost Basis ($10,000)
    # Because validation.py/reg_t_validation.py falls back to cost basis when price is 0.
    print(f"Equity with missing data: ${metrics_run_1.total_equity:,.2f}")
    
    if metrics_run_1.total_equity == 10000.0:
        print("✅ REPRODUCED: Equity is exactly $10,000 (Cost Basis Fallback Triggered).")
    else:
        print(f"❌ FAILED TO REPRODUCE: Equity is {metrics_run_1.total_equity}")


    # 3. Case B: Market Data Present (Price = $1100) -> 10% Gain
    print("\n[Case B] Testing with VALID market data ($1100/share)...")
    price_map_valid = {"NVDA": 1100.0}
    
    metrics_run_2 = calculate_reg_t_metrics(
        cash_balance=portfolio_cash,
        positions=positions,
        current_prices=price_map_valid,
        previous_sma=0.0
    )
    
    expected_equity = 1100.0 * 10
    print(f"Equity with valid data:   ${metrics_run_2.total_equity:,.2f}")
    
    if metrics_run_2.total_equity == 11000.0:
        print("✅ CORRECT BEHAVIOR: Equity reflects market value ($11,000).")
    else:
        print(f"❌ UNEXPECTED: Equity is {metrics_run_2.total_equity}")

if __name__ == "__main__":
    test_static_equity_bug()
