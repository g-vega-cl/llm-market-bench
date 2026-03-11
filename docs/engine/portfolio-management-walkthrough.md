# Step 11: Portfolio Management & Reg T Validation

This step ensures that our AI agents operate within realistic financial constraints, simulating a **Regulation T Margin Account** starting with **$10,000**.

## 1. The Goal
Instead of letting LLMs hallucinate unlimited funds, we inject their exact financial reality into every prompt. If an agent has $100 in cash but $40,000 in Buying Power (due to margin), it needs to know that.

## 2. Regulation T Logic
We strictly follow **Reg T** calculations for margin accounts.

### Key Formulas
| Metric | Calculation | Description |
| :--- | :--- | :--- |
| **Total Equity** | `Cash + Market Value of Positions` | The Net Liquidation Value (NLV). |
| **Maintenance Margin** | `0.33 * Market Value of Longs` | The minimum equity required to hold positions (33%). |
| **Available Funds** | `Total Equity - (Initial Margin: 57%)` | Capital available to open new positions. |
| **SMA** | `Max(Prior SMA, Available Funds)` | Special Memorandum Account. |
| **Buying Power** | `4 * Available Funds` | The max amount of stock you can buy intraday (4:1 Leverage). |

### 2a. Reg T Validation (Pre-Execution)
Before any trade is executed, we run `validate_trade_compliance` (in `reg_t_validation.py`) to ensure:
1. **Trade Cost <= Buying Power** (For BUY signals)
2. **Minimum Trade Value:** Total cost (Price * Quantity) must be at least **$1,000** for both **BUY and SELL** orders.
3. **Projected SMA >= SMA Floor (10% of Total Equity)**
4. **Account not in Liquidation**
5. **Market Data Robustness:** If `current_prices` fail (price = 0), the system values positions at `average_cost_basis`. This prevents "Negative Equity" hallucinations for margin accounts.
6. **Ticker Normalization:** All tickers are normalized to **UPPERCASE** across all validation and storage layers.

*Implementation: `apps/engine/execution/reg_t_validation.py`*

### 2b. Validation Logic (Pass/Fail Scenarios)
The validation logic strictly enforces the Buying Power limit.

1.  **Buying Power (BUY):** `estimated_cost <= buying_power`.
2.  **Portfolio Ownership (SELL):** `ticker in positions`.
3.  **Dynamic Minimum Size:** `estimated_cost >= max($1,000, 10% of BP or Equity)` for both BUY and SELL.
4.  **SMA Floor:** `projected_sma >= 10% * Total Equity`.
5.  **Account Not in Liquidation:** `available_funds >= 0`.

## 3. Persistent State (Database)
State is preserved in Supabase so agents "carry over" their positions to the next day.

### `portfolios` Table
One row per AI Model (e.g., `gpt-4o`).
- `cash_balance`: Starts at $10,000.
- `buying_power`: Updated after every trade and daily.
- `total_equity`: Updated after every trade and daily.
- `sma`: Stateful credit line updated after every trade and daily.
- `realized`: Total realized profit/loss.

### `portfolio_positions` Table
Tracks exact holdings.
- `ticker`: e.g., "NVDA"
- `quantity`: Number of shares.
- `average_cost_basis`: Weighted average price paid.

**Idempotent Tracking:**
To prevent "duplicate key" errors during high-frequency updates, the system uses an **UPSERT with on_conflict** pattern on the `(portfolio_id, ticker)` composite key. This ensures that scaling into a position correctly updates the existing record rather than attempting a conflicting insert.

### `position_pnl` View (Real-time P&L)
SQL view that calculates Profit/Loss without data duplication.
- `unrealized_pnl_usd`: Current dollar profit or loss.
- `unrealized_pnl_pct`: Percentage return based on cost basis.
- `current_price`: Latest price from the `market_data_cache`.

### UI Augmented Metrics
Calculated in the `PositionsTable` component:
- **Invested (Cash)**: `quantity * average_cost_basis`.
- **% of Portfolio**: `(Position Invested Cash / Total Portfolio Invested Cash) * 100`.


## 4. LLM Prompt Injection & Awareness
Before the LLM analyzes news, we insert a snapshot of its financial health. The LLM is also given explicit instructions on **SMA Management Rules**, the **10% Safety Floor**, and the **$1,000 Minimum Purchase Rule**.

**System Prompt Addition:**
```text
### Current Portfolio Status:
Cash Balance: $10,000.00
Total Equity: $10,000.00
Buying Power: $40,000.00
SMA: $10,000.00
Excess Liquidity: $10,000.00
Maintenance Margin: $0.00

Current Positions:
- None
```

## 5. Decision Making (Allocation %)
LLMs can now output an `allocation_percentage` (0-100%) in their JSON decision. 
- **BUY Logic:** The engine calculates `Allocation % * Buying Power` to determine the total USD to spend.
    - **Smart Bump:** If the calculated spend is below **$1,000**, the engine automatically "bumps" the spend to $1,000 (if Buying Power allows).
    - **Quantity:** The final share quantity is calculated based on the market price. If rounding down results in a value below $1,000, one share is added if affordable.
- **SELL Logic:** **MANDATORY HARD TOOL ENFORCEMENT.** 
    - **History Scan:** The engine performs a server-side scan of the conversation history to verify that a `sell_X_percent` tool was actually called for that ticker.
    - **Hallucination Check:** If an agent claims `sell_tool_called: true` but the history scan fails to find the call, the trade is rejected.
    - **Minimum Value:** Even if the tool is called, the total proceeds must be >= $1,000. Sells below this threshold (dust trades) are rejected as `REJECTED_MARGIN`.
- **Dynamic Fallbacks:** 
    - If `allocation_percentage` is missing, the system defaults to **5%** (then applies the $1,000 bump logic).

## 5a. Portfolio Ownership Guardrails (SELL)
To prevent agents from opening "hallucinated" short positions, the system enforces strict ownership checks:
1. **Pipeline Check:** Before execution, the engine verifies the ticker is in the model's `portfolio_positions`.
2. **Execution Check:** If a model attempts to sell more than it owns (e.g. "Sell 20 shares" while holding 10), the trade is capped at the owned quantity (10 shares), and the position is closed.
3. **Hard Tool Enforcement:** Unauthorized SELL attempts or sells where tool usage was hallucinated (self-reported but not found in history) are logged in the `decisions` table with status `REJECTED_OWNERSHIP`, `REJECTED_TOOL_USAGE`, or `REJECTED_MARGIN`.

## 6. Verification
We verify this logic with standard scenarios and dedicated guardrail tests (see `apps/engine/tests/test_sell_guardrails.py`), ensuring the system correctly handles:
- Leverage (Borrowing)
- Margin Calls (Liquidation scenarios)
- **SELL Ownership Enforcement** (Preventing naked shorts)
- **Allocation-to-Quantity conversion**
