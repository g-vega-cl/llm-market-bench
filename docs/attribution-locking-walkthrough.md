# Step 13: Attribution Locking

## Goal
To establish a verifiable, immutable link between an executed `Trade` and the AI `Decision` that caused it. This creates a machine-auditable "Audit Trail" from raw newsletter text -> reasoning -> decision -> execution.

## The Problem
In Step 12, we execute trades and generate a `TradeID`. However, the original `Decision` record (created in Step 7) is initially "floating" without knowledge of the trade outcome. Without linking them, we cannot confirm later why a specific trade happened.

## The Solution
We update the `decisions` table to store the `trade_id` as a Foreign Key. This "locks" the attribution: a Trade cannot exist without a Decision (conceptually), and we now can query "Show me the reasoning for Trade X".

## Schema
### `decisions` Table Update
```sql
ALTER TABLE decisions
ADD COLUMN trade_id UUID REFERENCES trades(id);
```

### `trades` Table (Reference)
```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    ticker TEXT NOT NULL,
    signal TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price NUMERIC NOT NULL,
    executed_at TIMESTAMPTZ DEFAULT now()
);
```

## Implementation Logic

The locking happens in the main execution loop in `apps/engine/main.py` immediately after a successful trade execution.

### Logic Flow

1. **Validation**: The decision passes all guardrails and Reg T checks.
2. **Execution**: `portfolio.execute_trade(...)` runs and returns a `trade_id`.
3. **Locking**: The engine calls `save_decision` with the new `trade_id`.
   - The system performs an `UPSERT` on the decision record.
   - It updates the status to `EXECUTED`.
   - It sets the `trade_id` column to the UUID returned by step 2.

### Code Example (`main.py`)

```python
# 1. Execute the trade
trade_id = await portfolio.execute_trade(
    d.ticker, 
    qty, 
    exec_price, 
    d.signal
)

if trade_id:
    status = "EXECUTED"
    # ...

# 2. Lock the Attribution (Link Decision -> Trade)
save_decision(
    sb_client, 
    d, 
    status=status, 
    metadata=meta,
    trade_id=str(trade_id)  # <--- The Link
)
```

## Verification

We verified this logic with integration tests that simulate the full pipeline:

1. **Trade Execution**: Confirmed `trade_id` is generated.
2. **Attribution Update**: Verified `decisions` table contains the correct `trade_id`.
3. **Hold/Reject Scenarios**: Confirmed `trade_id` remains `NULL` for decisions that didn't result in a trade.
