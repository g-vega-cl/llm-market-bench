# Profit & Loss (P&L) Calculation Methodology

## Overview

The AI Wall Street engine implements a **weighted average cost basis** method for tracking P&L across all portfolio positions. This document details the calculation methodology for both **unrealized** (paper) and **realized** (actual) P&L.

---

## Table of Contents

1. [Average Cost Basis Tracking](#average-cost-basis-tracking)
2. [Unrealized P&L Calculation](#unrealized-pnl-calculation)
3. [Realized P&L Calculation](#realized-pnl-calculation)
4. [Edge Cases](#edge-cases)
5. [Database Schema](#database-schema)
6. [Testing](#testing)

---

## Average Cost Basis Tracking

### Methodology

The system uses a **weighted average cost basis** method, which calculates the average price paid across all purchases of a security. This is the standard method for retail brokerage accounts and provides tax-lot agnostic tracking.

### Formula

```
New Average Cost Basis = (Old Total Cost + New Purchase Cost) / New Total Quantity

Where:
- Old Total Cost = Current Quantity × Current Average Cost Basis
- New Purchase Cost = Purchase Quantity × Purchase Price
- New Total Quantity = Current Quantity + Purchase Quantity
```

### Implementation (BUY Transactions)

**File:** `apps/engine/execution/portfolio.py` (Lines 306-317)

```python
if signal.upper() == "BUY":
    self.cash_balance -= total_cost

    # Update Position
    if ticker in self.positions:
        pos = self.positions[ticker]
        old_cost = pos.average_cost_basis * pos.quantity
        new_cost = old_cost + total_cost
        pos.quantity += quantity
        pos.average_cost_basis = new_cost / pos.quantity
    else:
        self.positions[ticker] = Position(
            ticker=ticker,
            quantity=quantity,
            average_cost_basis=price
        )
```

### Example: Multiple Purchases

| Transaction | Quantity | Price | Total Cost | New Avg Cost Basis |
|------------|----------|-------|-----------|-------------------|
| BUY 1      | 100      | $150  | $15,000   | $150.00           |
| BUY 2      | 100      | $200  | $20,000   | $175.00           |
| BUY 3      | 50       | $120  | $6,000    | $160.00           |

**Calculation for BUY 3:**
```
Old Total Cost = 200 × $175 = $35,000
New Purchase Cost = 50 × $120 = $6,000
New Total Cost = $35,000 + $6,000 = $41,000
New Total Quantity = 200 + 50 = 250
New Average Cost Basis = $41,000 / 250 = $164.00
```

---

## Unrealized P&L Calculation

### Methodology

Unrealized P&L represents the **paper profit or loss** on positions that are still held. It compares the current market price to the average cost basis.

### Formula

```
Unrealized P&L (USD) = (Current Price - Average Cost Basis) × Quantity

Unrealized P&L (%) = ((Current Price / Average Cost Basis) - 1) × 100
```

### Implementation (SQL View)

**File:** `supabase/migrations/20260121150000_create_position_pnl_view.sql`

```sql
CREATE OR REPLACE VIEW public.position_pnl AS
SELECT
    p.id as position_id,
    p.portfolio_id,
    port.owner_id,
    p.ticker,
    p.quantity,
    p.average_cost_basis,
    m.price AS current_price,
    m.fetched_at AS price_fetched_at,
    (COALESCE(m.price, p.average_cost_basis) - p.average_cost_basis) * p.quantity AS unrealized_pnl_usd,
    CASE
        WHEN p.average_cost_basis > 0 THEN ((COALESCE(m.price, p.average_cost_basis) / p.average_cost_basis) - 1) * 100
        ELSE 0
    END AS unrealized_pnl_pct
FROM
    public.portfolio_positions p
JOIN
    public.portfolios port ON p.portfolio_id = port.id
LEFT JOIN
    public.market_data_cache m ON p.ticker = m.ticker;
```

### Implementation (Python - Portfolio Summary)

**File:** `apps/engine/execution/portfolio.py` (Lines 145-156)

```python
for ticker, pos in self.positions.items():
    curr_price = current_prices.get(ticker, 0.0)
    pl = (curr_price - pos.average_cost_basis) * pos.quantity
    pl_pct = ((curr_price / pos.average_cost_basis) - 1) * 100 if pos.average_cost_basis else 0
    summary.append(
        f"- {ticker}: {pos.quantity} shares @ ${pos.average_cost_basis:.2f} "
        f"(Curr: ${curr_price:.2f}, P/L: ${pl:.2f} / {pl_pct:.1f}%)"
    )
```

### Example

| Position | Avg Cost | Current Price | Quantity | Unrealized P&L (USD) | Unrealized P&L (%) |
|----------|----------|---------------|----------|---------------------|-------------------|
| AAPL     | $150.00  | $175.00       | 100      | +$2,500.00          | +16.67%           |
| MSFT     | $300.00  | $280.00       | 50       | -$1,000.00          | -6.67%            |

---

## Realized P&L Calculation

### Methodology

Realized P&L is calculated **only when shares are sold**. It represents the actual profit or loss from the portion of the position that was closed. The average cost basis is used to determine the cost of the shares sold.

### Formula

```
Realized P&L (USD) = (Sell Price - Average Cost Basis) × Quantity Sold

Realized P&L (%) = ((Sell Price / Average Cost Basis) - 1) × 100
```

### Implementation (SELL Transactions)

**File:** `apps/engine/execution/portfolio.py` (Lines 297-392)

```python
# Capture current average cost context for P&L calculation (for SELL signals)
# We need the cost basis BEFORE it might be updated/deleted by the sell
old_avg_cost = None
if signal.upper() == "SELL" and ticker in self.positions:
    old_avg_cost = self.positions[ticker].average_cost_basis

# ... position update logic ...

# Enrich with PnL for SELL trades
if signal.upper() == "SELL" and old_avg_cost is not None:
    realized_pnl = (price - old_avg_cost) * quantity
    realized_pnl_pct = ((price / old_avg_cost) - 1) * 100 if old_avg_cost > 0 else 0
    trade_data["realized_pnl"] = realized_pnl
    trade_data["realized_pnl_pct"] = realized_pnl_pct
```

### Key Behavior: Partial Sales

When selling **only a portion** of a position:
- The average cost basis of the **remaining shares stays unchanged**
- Only the quantity is reduced
- Realized P&L is calculated only on the shares sold

**Example:**
```
Initial Position: 200 shares @ $175 avg cost
SELL 50 shares @ $200

Realized P&L = ($200 - $175) × 50 = +$1,250.00 (+14.29%)
Remaining Position: 150 shares @ $175 avg cost (unchanged)
```

### Example: Full Position Sale

| Transaction | Quantity | Avg Cost | Sell Price | Realized P&L (USD) | Realized P&L (%) |
|-------------|----------|----------|------------|-------------------|-----------------|
| SELL All    | 100      | $150.00  | $200.00    | +$5,000.00        | +33.33%         |

### Example: Partial Sale Sequence

```
Initial: 300 shares @ $100 avg cost

SELL 100 @ $150 → Realized: +$5,000 (50% gain)
Remaining: 200 shares @ $100 avg cost

SELL 100 @ $200 → Realized: +$10,000 (100% gain)
Remaining: 100 shares @ $100 avg cost

SELL 100 @ $180 → Realized: +$8,000 (80% gain)
Remaining: 0 shares (position closed)

Total Realized P&L: +$23,000
```


### Multi-Part Trading Scenario (Comprehensive Example)

To illustrate how the average cost basis moves through multiple buys and sells, consider this sequence for a single ticker:

| Step | Action | Qty | Price | Total Cost | Avg Cost Basis | Realized P&L | Remaining Qty |
|------|--------|-----|-------|------------|----------------|--------------|---------------|
| 1    | BUY    | 10  | $100  | $1,000     | $100.00        | -            | 10            |
| 2    | BUY    | 10  | $120  | $1,200     | $110.00        | -            | 20            |
| 3    | SELL   | 5   | $130  | $650       | $110.00        | +$100.00     | 15            |
| 4    | BUY    | 5   | $150  | $750       | $120.00        | -            | 20            |
| 5    | SELL   | 20  | $160  | $3,200     | $120.00        | +$800.00     | 0             |

**Detailed Calculations:**

*   **Step 2 (BUY):** `(10 * 100 + 10 * 120) / 20 = $110.00`
*   **Step 3 (SELL):** `(130 - 110) * 5 = $100.00`. Remaining avg cost stays `$110.00`.
*   **Step 4 (BUY):** `(15 * 110 + 5 * 150) / 20 = (1650 + 750) / 20 = $120.00`
*   **Step 5 (SELL):** `(160 - 120) * 20 = $800.00`. Final quantity is 0.

---

## Edge Cases

### 1. Zero Cost Basis

When the average cost basis is $0 (e.g., stock grants, warrants, spin-offs):

```python
realized_pnl_pct = ((price / old_avg_cost) - 1) * 100 if old_avg_cost > 0 else 0
```

- **Realized P&L (USD):** Full sale proceeds (since cost was $0)
- **Realized P&L (%):** Returns 0% to avoid division by zero

### 2. Selling More Than Owned

The system includes a guardrail to prevent selling more shares than owned:

```python
if quantity > pos.quantity:
    logger.warning(
        f"Attempted to sell {quantity} shares of {ticker} but only held {pos.quantity}. "
        "Capping sell to owned quantity."
    )
    quantity = pos.quantity
```

### 3. Selling Without Position

If an agent attempts to sell a ticker they don't own:

```python
if ticker not in self.positions:
    logger.warning(f"REJECTED: Selling {ticker} but not held in portfolio.")
    return None
```

The trade is **rejected** and no P&L is recorded.

### 4. Complete Position Closure

When a position is fully closed (quantity reaches 0):
- The position is removed from `portfolio_positions`
- The final realized P&L is recorded in the `trades` table
- No further P&L tracking occurs for that ticker

---

## Database Schema

### Portfolio Positions Table

```sql
CREATE TABLE portfolio_positions (
    id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    ticker TEXT NOT NULL,
    quantity INT NOT NULL,
    average_cost_basis NUMERIC NOT NULL,
    
    UNIQUE(portfolio_id, ticker),
    CONSTRAINT quantity_not_negative CHECK (quantity >= 0)
);
```

### Trades Ledger

```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY,
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    ticker TEXT NOT NULL,
    signal TEXT NOT NULL,  -- 'BUY' or 'SELL'
    quantity INTEGER NOT NULL,
    price NUMERIC NOT NULL,
    total_cost NUMERIC NOT NULL,
    executed_at TIMESTAMPTZ DEFAULT now(),
    decision_id UUID,
    
    -- P&L tracking (for SELL signals)
    realized_pnl NUMERIC,
    realized_pnl_pct NUMERIC
);
```

### Position P&L View

```sql
CREATE VIEW public.position_pnl AS
SELECT
    p.id as position_id,
    p.portfolio_id,
    port.owner_id,
    p.ticker,
    p.quantity,
    p.average_cost_basis,
    m.price AS current_price,
    m.fetched_at AS price_fetched_at,
    (COALESCE(m.price, p.average_cost_basis) - p.average_cost_basis) * p.quantity AS unrealized_pnl_usd,
    CASE
        WHEN p.average_cost_basis > 0 THEN ((COALESCE(m.price, p.average_cost_basis) / p.average_cost_basis) - 1) * 100
        ELSE 0
    END AS unrealized_pnl_pct
FROM
    public.portfolio_positions p
JOIN
    public.portfolios port ON p.portfolio_id = port.id
LEFT JOIN
    public.market_data_cache m ON p.ticker = m.ticker;
```

---

## Testing

### Test Coverage

Comprehensive tests are located in: `apps/engine/tests/test_pnl_calculations.py`

**Test Categories:**

1. **Average Cost Basis (BUY)**
   - `test_initial_buy_sets_cost_basis`
   - `test_second_buy_updates_weighted_average`
   - `test_multiple_buys_at_different_prices`

2. **Realized P&L (SELL)**
   - `test_full_position_sale_realizes_correct_pnl`
   - `test_partial_sale_realizes_proportional_pnl`
   - `test_partial_sale_with_loss`
   - `test_multiple_sells_same_position`

3. **Complex Scenarios**
   - `test_buy_sell_buy_sequence`
   - `test_multi_part_buy_sell_sequence`
   - `test_sell_without_position_returns_none`
   - `test_zero_cost_basis_edge_case`

4. **Portfolio Summary**
   - `test_get_portfolio_summary_includes_pnl`

### Running Tests

```bash
cd apps/engine
pytest tests/test_pnl_calculations.py -v
```

### Verification Script

A manual verification script is available: `apps/engine/verify_pnl_view.py`

```bash
python apps/engine/verify_pnl_view.py
```

This script:
1. Creates a test position with known cost basis
2. Inserts test market data
3. Queries the `position_pnl` view
4. Asserts correct P&L calculations
5. Cleans up test data

---

## Audit Trail

The system maintains a complete audit trail for all P&L calculations:

1. **Decision → Trade Linkage:** Every trade is linked to the decision that triggered it via `decision_id`
2. **Trade Ledger:** All executed trades are stored immutably in the `trades` table
3. **Position History:** Changes to `portfolio_positions` are tracked with timestamps
4. **Realized P&L:** Each SELL trade records both USD and percentage P&L
5. **Unrealized P&L:** The `position_pnl` view provides real-time P&L for all open positions

### Attribution Chain

```
News → Reasoning → Decision ↔ Trade → P&L
```

This chain allows full reconstruction of:
- Why a trade was made (reasoning)
- At what price (execution)
- What the cost basis was (average cost tracking)
- What the outcome was (realized/unrealized P&L)

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| **Cost Basis Method** | Weighted Average |
| **Unrealized P&L** | Current Price vs Avg Cost |
| **Realized P&L** | Calculated on SELL only |
| **Partial Sales** | Avg cost unchanged, P&L on sold portion |
| **Edge Cases** | Zero cost basis, over-selling, no position |
| **Database** | `portfolio_positions`, `trades`, `position_pnl` view |
| **Audit Trail** | Full decision → trade → P&L linkage |

This methodology ensures accurate, auditable P&L tracking across all AI agent portfolios while maintaining consistency with standard brokerage accounting practices.
