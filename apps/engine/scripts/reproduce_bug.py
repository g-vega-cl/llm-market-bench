import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio

from execution.portfolio import Portfolio, Position


async def reproduce():
    print("--- Simulating Portfolio Trades ---")
    p = Portfolio(owner_id="test-agent")
    # Simulate initial state
    p.cash_balance = 10000.00
    p.sma = 10000.00
    p.positions = {}
    
    print(f"Initial: Cash={p.cash_balance}, SMA={p.sma}, Equity=10000.00")
    
    # Trade 1: Buy GLD
    # 26 shares @ 447.82
    ticker1 = "GLD"
    qty1 = 26
    price1 = 447.82
    total_cost1 = qty1 * price1
    print(f"\nBuying {qty1} {ticker1} @ {price1} (Total: {total_cost1})")
    
    # Mock execute_trade logic (manually to avoid DB calls)
    p.cash_balance -= total_cost1
    p.positions[ticker1] = Position(ticker=ticker1, quantity=qty1, average_cost_basis=price1)
    margin_req1 = total_cost1 * 0.57
    p.sma -= margin_req1
    
    metrics1 = p.calculate_reg_t_metrics({ticker1: price1})
    print(f"Post-Trade 1: Cash={p.cash_balance}, SMA={p.sma}, Equity={metrics1.total_equity}")
    print(f"Metrics 1: IB={metrics1.initial_margin_req}, BP={metrics1.buying_power}, Realized={metrics1.realized}")

    # Trade 2: Buy NFLX
    # 12 shares @ 84.085
    ticker2 = "NFLX"
    qty2 = 12
    price2 = 84.085
    total_cost2 = qty2 * price2
    print(f"\nBuying {qty2} {ticker2} @ {price2} (Total: {total_cost2})")
    
    p.cash_balance -= total_cost2
    p.positions[ticker2] = Position(ticker=ticker2, quantity=qty2, average_cost_basis=price2)
    margin_req2 = total_cost2 * 0.57
    p.sma -= margin_req2
    
    metrics2 = p.calculate_reg_t_metrics({ticker1: price1, ticker2: price2})
    print(f"Post-Trade 2: Cash={p.cash_balance}, SMA={p.sma}, Equity={metrics2.total_equity}")
    print(f"Metrics 2: IB={metrics2.initial_margin_req}, BP={metrics2.buying_power}, Realized={metrics2.realized}")

    print("\n--- Final State vs User Data ---")
    print(f"Calculated Cash: {p.cash_balance}")
    print("User Cash: -5427.145")
    print(f"Calculated Equity: {metrics2.total_equity}")
    print("User Equity: 7225.195")
    
if __name__ == "__main__":
    asyncio.run(reproduce())
