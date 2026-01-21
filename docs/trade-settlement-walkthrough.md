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

## 3. Database Updates
We perform a transactional update to `supabase`:

1.  **`portfolios` table:**
    -   Update `cash_balance`.
    -   Update `sma`.
    -   Update `last_updated_at`.
2.  **`portfolio_positions` table:**
    -   `UPSERT` the position row with new quantity/cost.
    -   OR `DELETE` the row if quantity is zero.
## 4. Quantity Calculation (Allocation %)
Before settlement, the engine converts the LLM's `allocation_percentage` into a share count:
- **BUY:** `Qty = (Allocation % * Buying Power) / Market Price`.
- **SELL:** `Qty = (Allocation % * Current Quantity)`.
- **Fallback:** If `allocation_percentage` is missing, use **5%**. If resulting `Qty` is 0, default to **1 share**.

## 4. Example Flow
**Scenario:** Agent buys 10 AAPL @ $150.
*   **Initial:** Cash $10,000. Positions: None.
*   **Execution:** Cost $1,500.
*   **Final:** Cash $8,500. Positions: { AAPL: 10 shares @ $150 }.

**Scenario:** Agent sells 5 AAPL @ $200 (Profit).
*   **Initial:** Cash $8,500. Positions: { AAPL: 10 }.
*   **Execution:** Proceeds $1,000.
*   **Final:** Cash $9,500. Positions: { AAPL: 5 shares }.
