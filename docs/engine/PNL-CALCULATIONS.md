# Profit & Loss (P&L) Calculation Methodology

The engine uses **weighted average cost basis** for tracking P&L across all portfolio positions.

## Core Formulas

### Average Cost Basis (BUY)

```
New Average Cost Basis = (Old Total Cost + New Purchase Cost) / New Total Quantity
```

Implementation: `apps/engine/execution/portfolio.py` (BUY transaction handler)

### Unrealized P&L

```
Unrealized P&L (USD) = (Current Price - Average Cost Basis) × Quantity
Unrealized P&L (%)     = ((Current Price / Average Cost Basis) - 1) × 100
```

Calculated on-the-fly via SQL view `position_pnl` for real-time display.

### Realized P&L (SELL)

```
Realized P&L (USD) = (Sell Price - Average Cost Basis) × Quantity Sold
Realized P&L (%)     = ((Sell Price / Average Cost Basis) - 1) × 100
```

Calculated only when shares are sold. Implementation: `apps/engine/execution/portfolio.py` (SELL transaction handler).

**Partial Sales**: When selling only part of a position, the average cost basis of remaining shares stays unchanged. P&L is calculated only on the sold portion.

Example:
```
Initial: 200 shares @ $175 avg cost
SELL 50 @ $200 → Realized P&L: ($200 - $175) × 50 = +$1,250 (+14.29%)
Remaining: 150 shares @ $175 avg cost (unchanged)
```

## Edge Cases

| Case | Handling |
|------|----------|
| Zero cost basis (stock grants, warrants) | Full sale proceeds as realized P&L USD; 0% returned to avoid div/0 |
| Selling more than owned | Quantity capped to owned amount with warning |
| Selling ticker not held | Trade rejected, no P&L recorded |
| Full position closure (qty → 0) | Position removed from `portfolio_positions`, final P&L in `trades` |

## Database Schema

**`portfolio_positions`**: `id`, `portfolio_id`, `ticker`, `quantity`, `average_cost_basis` — unique on `(portfolio_id, ticker)`

**`trades`**: `id`, `portfolio_id`, `ticker`, `signal`, `quantity`, `price`, `total_cost`, `realized_pnl`, `realized_pnl_pct`, `decision_id`

**`position_pnl`** (SQL view): Joins `portfolio_positions` with `market_data_cache` for live unrealized P&L

## Audit Trail

```
News → Reasoning → Decision ↔ Trade → P&L
```

Every trade links back to its triggering decision via `decision_id`. Complete reconstruction of why, at what price, at what cost basis, and with what outcome.

## Key Files

- `apps/engine/execution/portfolio.py` — BUY/SELL P&L calculation
- `supabase/migrations/20260121150000_create_position_pnl_view.sql` — Live P&L view
- `apps/engine/tests/test_pnl_calculations.py` — Test suite
