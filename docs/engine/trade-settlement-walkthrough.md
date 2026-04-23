# Step 12: Trade Settlement

This step handles the final **Execution** of the trade. Once a decision has passed both **Pre-Market Validation** (Existence/Price) and **Reg T Validation** (Affordability), it is "settled" into the ledger.

## 1. The Goal
To permanently update the agent's **Cash Balance** and **Holdings** in the database to reflect the trade, creating a persistent state for the next day's run.

## 2. Settlement Logic
Implementation: `apps/engine/execution/portfolio.py` -> `execute_trade()`

### BUY Execution
1.  **Cost Calculation:** `Total Cost = Quantity * Execution Price`
2.  **Cash Update:** `New Cash = Old Cash - Total Cost`
3.  **Position Update:**
    -   If Ticker is already held:
        -   Update **Quantity**: `Old Qty + New Qty`
        -   Update **Average Cost Basis**: Weighted Average of (Old Cost) and (New Trade Price).
    -   If Ticker is new:
        -   Create new entry with `Quantity` and `Cost Basis = Execution Price`.
4.  **SMA Update:** `SMA = SMA - (57% * Total Cost)`. (Buying consumes margin line).

### SELL Execution
1.  **Ownership Check:** Verify ticker is held in `portfolio_positions`. Reject if not owned (`REJECTED_OWNERSHIP`).
2.  **Quantity Capping:** If requested sell quantity > owned quantity, cap the trade to the total owned amount (close position).
3.  **Proceeds Calculation:** `Total Proceeds = Final Quantity * Execution Price`
4.  **Cash Update:** `New Cash = Old Cash + Total Proceeds`
5.  **Position Update:**
    -   Reduce `Quantity`.
    -   If `Quantity` becomes 0, remove position from database.
    -   *Note: Cost Basis does not change during a SELL (First-In-First-Out or Weighted Avg remains constant per share).*
6.  **SMA Update:** `SMA = SMA + (57% * Proceeds)`. (Selling releases margin).

## 3. Atomic Database Updates
To prevent "Phantom Cash Losses" (where cash is deducted but no position is recorded), we follow a strict **"Commit at the End"** sequence. If any step fails, the function returns `None` and the Agent's Portfolio remains in its previous state.

### Pre-Step: Decision ID Attribution Lock
Before trade execution, the engine saves the decision with `status="VALIDATED"` to obtain a `decision_id`. This is required because:
- The `trades` table has a foreign key constraint referencing the `decisions` table.
- This creates the initial link in the audit trail before execution begins.

### Execution Sequence

1.  **`portfolio_positions` table:**
    -   `UPSERT` the position row with new quantity/cost (Tickers are normalized to **UPPERCASE**).
    -   OR `DELETE` the row if quantity reached zero.
2.  **`trades` table:**
    -   Insert a new record to generate a unique `TradeID`. This serves as the source of truth for the audit trail.
    -   **The trade record includes the `decision_id` from the pre-step**, establishing the Decision → Trade link.
3.  **`portfolios` table (The "Commit"):**
    -   **Only after** the previous two steps succeed, update the account's `cash_balance` and `sma`.
4.  **Final Persistence:**
    -   Recalculate and save updated metrics (Total Equity, Buying Power) to the `portfolios` table for dashboard consistency.
5.  **Post-Step: Attribution Completion**
    -   After successful trade execution, the engine updates the decision record again with `status="EXECUTED"` and the `trade_id`.
    -   This completes the **bidirectional attribution lock**: `Decision ↔ Trade`.
## 4. Quantity Calculation (Allocation %)
- For **BUY** trades, the engine uses the `allocation_percentage` (1-100%) against available **Buying Power**.
- **Dynamic Minimum:** If `Price * Qty < 10% of BP/Equity`, the engine attempts to "Bump" the allocation to meet the threshold if sufficient BP exists.
- **SELL:** **Mandatory Tool Calculation.** LLMs must call a sell percentage tool to get the `quantity`. If a tool is used, the absolute $1,000 minimum trade floor is waived.
- **Fallback:** If `allocation_percentage` is missing for BUYS, use **5%**. For SELLS, the trade is REJECTED if no tool was called.

## 5. Example Flow
**Scenario:** Agent buys 10 AAPL @ $150.
*   **Initial:** Cash $10,000. Positions: None.
*   **Execution:** Cost $1,500.
*   **Final:** Cash $8,500. Positions: { AAPL: 10 shares @ $150 }.

**Scenario:** Agent sells 5 AAPL @ $200 (Profit).
*   **Initial:** Cash $8,500. Positions: { AAPL: 10 }.
*   **Execution:** Proceeds $1,000.
*   **Final:** Cash $9,500. Positions: { AAPL: 5 shares }.

---

## 6. Third-Party Audit: Alpaca Paper Trading

Every trade that survives the settlement sequence is **fire-and-forget mirrored** to Alpaca's paper trading API. This provides an external, immutable audit trail for public verification.

### Design Principles
- **Supabase remains the source of truth.** Alpaca is an audit mirror, not the ledger.
- **Fire-and-forget.** The Alpaca submission is wrapped in `asyncio.create_task()` and does not block the main execution flow.
- **Failure isolation.** If Alpaca is down, rejects the order, or throws an exception, the internal trade still succeeds. Only the `alpaca_status` column is updated to `ERROR`.
- **Agent tagging.** Each order uses a `client_order_id` formatted as `{agent_id}__{ticker}__{signal}__{trade_id}`, allowing the Alpaca dashboard to be filtered by individual AI agents.

### Order Parameters
- **Type:** `DAY` limit order at the same price the engine used for settlement.
- **Side:** `BUY` or `SELL` matching the engine signal.
- **Quantity:** Same share count as the internal ledger entry.
- **Time in Force:** `DAY` (expires at market close if unfilled).

### Implementation
- **File:** `apps/engine/execution/alpaca_broker.py`
- **Hook:** `apps/engine/execution/portfolio.py` -> `execute_trade()` (Step 5, after metrics save)
- **Toggle:** `ALPACA_ENABLED` is a hardcoded constant in `core/config.py` (`True` by default). Set to `False` to disable mirroring without code changes.

### Verification
After a trade executes, check:
1. **Supabase** `trades` row: `alpaca_order_id`, `alpaca_status`, `alpaca_submitted_at` populated.
2. **Alpaca Paper Dashboard:** [paper.alpaca.markets/orders](https://paper.alpaca.markets/orders) — filter by `client_order_id` containing the agent name.
