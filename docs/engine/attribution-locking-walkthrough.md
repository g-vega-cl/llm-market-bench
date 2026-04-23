# Step 13: Attribution Locking

## Goal
To establish a verifiable, immutable link between an executed `Trade` and the AI `Decision` that caused it. This creates a machine-auditable "Audit Trail" from raw newsletter text -> reasoning -> decision -> execution. Additionally, every executed trade is mirrored to **Alpaca Paper Trading** for third-party public auditability.

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

The locking happens in the main execution loop in `apps/engine/main.py` using a **two-phase commit pattern** to ensure referential integrity between decisions and trades.

### Logic Flow

1. **Validation**: The decision passes all guardrails and Reg T checks.
2. **Pre-Trade Save (Phase 1)**: The engine calls `save_decision` with `status="VALIDATED"` to create the decision record and obtain a `decision_id`.
   - This `decision_id` is required as a foreign key in the `trades` table.
   - At this point, the decision is logged but not yet linked to a trade.
3. **Execution**: `portfolio.execute_trade(...)` runs with the `decision_id` and returns a `trade_id`.
   - The trade record is created with a reference to the `decision_id`.
4. **Attribution Lock (Phase 2)**: The engine calls `save_decision` again to update the decision record.
   - The system performs an `UPSERT` on the decision record.
   - It updates the status to `EXECUTED`.
   - It sets the `trade_id` column to the UUID returned by step 3.
   - This completes the bidirectional link: `Decision ↔ Trade`.

### Code Example (`main.py`)

```python
# Phase 1: Save decision to get decision_id (required for trade foreign key)
decision_row = save_decision(
    sb_client,
    d,
    status="VALIDATED",  # Initial status before execution
    metadata=meta
)
decision_id = decision_row.get("id")

# Execute the trade with the decision_id reference
trade_id = await portfolio.execute_trade(
    d.ticker,
    qty,
    exec_price,
    d.signal,
    decision_id=decision_id  # Link trade back to decision
)

if trade_id:
    status = "EXECUTED"
    meta = {"trade_id": str(trade_id), "info": f"Executed {d.signal} {qty} @ ${exec_price:.2f}"}
else:
    status = "ERROR_EXECUTION"
    meta = {"info": "Execution Failed"}

# Phase 2: Lock the attribution (Link Decision -> Trade)
save_decision(
    sb_client,
    d,
    status=status,
    metadata=meta,
    trade_id=str(trade_id) if trade_id else None  # <--- The Link
)
```

### Why Two Saves?

The two-phase pattern is necessary because:

1. **Foreign Key Constraint**: The `trades` table requires a `decision_id` foreign key reference.
2. **Circular Dependency**: We need the `decision_id` before creating the trade, but the trade generates the `trade_id` needed to complete the decision record.
3. **Atomic Integrity**: If trade execution fails, the initial `VALIDATED` decision remains as an audit trail showing the intent was validated but not executed.

## Verification

We verified this logic with integration tests that simulate the full pipeline:

1. **Trade Execution**: Confirmed `trade_id` is generated.
2. **Attribution Update**: Verified `decisions` table contains the correct `trade_id`.
3. **Hold/Reject Scenarios**: Confirmed `trade_id` remains `NULL` for decisions that didn't result in a trade.
4. **Two-Phase Save**: Tests confirm that executed decisions result in exactly **two** `save_decision` calls:
   - First call: `status="VALIDATED"` (obtains `decision_id`)
   - Second call: `status="EXECUTED"` with `trade_id` (completes the attribution lock)
