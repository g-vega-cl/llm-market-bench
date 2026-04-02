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
2. **Minimum Trade Value:** Total cost (Price * Quantity) must be at least **$1,000** for BUY orders. For SELL orders, this floor is waived if a specific sell tool is used.
3. **Projected SMA >= SMA Floor (10% of Total Equity)**
4. **Account not in Liquidation**
5. **Market Data Robustness:** If `current_prices` fail (price = 0), the system values positions at `average_cost_basis`. This prevents "Negative Equity" hallucinations for margin accounts.
6. **Ticker Normalization:** All tickers are normalized to **UPPERCASE** across all validation and storage layers.

*Implementation: `apps/engine/execution/reg_t_validation.py`*

### 2b. Validation Logic (Pass/Fail Scenarios)
The validation logic strictly enforces the Buying Power limit.

1.  **Buying Power (BUY):** `estimated_cost <= buying_power`.
2.  **Portfolio Ownership (SELL):** `ticker in positions`.
3.  **Dynamic Minimum Size:** `estimated_cost >= max($1,000, 10% of BP or Equity)` for BUYS. For SELLS, the $1,000 floor applies unless bypassed via a sell tool.
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


### 4. LLM Prompt Injection & Awareness
Before the LLM analyzes news, we insert a snapshot of its financial health. This includes the current market price for every holding (fetched in parallel across all portfolios to ensure consistency and efficiency) and a **Recently Executed Trades** list with **granular "time ago" formatting** (e.g., "5m ago", "12h ago"). This ensures models are aware of their recent momentum and don't repeat trades on the same catalysts.

The LLM is also given explicit instructions on **SMA Management Rules**, the **10% Safety Floor**, and the **$1,000 Minimum Purchase Rule**.

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

Recently Executed Trades (Last 48h):
- BUY NVDA: 10 @ $900.00 (2h ago) - Reason: AI demand is surging for chips.
```

## 5. Decision Making (Allocation %)
LLMs can now output an `allocation_percentage` (0-100%) in their JSON decision.
- **BUY Logic:** The engine calculates `Allocation % * Buying Power` to determine the total USD to spend.
    - **Smart Bump:** If the calculated spend is below **$1,000**, the engine automatically "bumps" the spend to $1,000 (if Buying Power allows).
    - **Quantity:** The final share quantity is calculated based on the market price. If rounding down results in a value below $1,000, one share is added if affordable.
- **SELL Logic:** **MANDATORY HARD TOOL ENFORCEMENT.**
    - **History Scan:** The engine performs a server-side scan of the conversation history to verify that a `sell_X_percent` tool was actually called for that ticker.
    - **Hallucination Check:** If an agent claims `sell_tool_called: true` but the history scan fails to find the call, the trade is rejected.
    - **Minimum Value:** By default, total proceeds must be >= $1,000. However, if a specific sell percentage tool is called, this threshold is waived to allow for precision exits and clearing "dust" trades.
    - **10% Minimum Position Rule (AUTOMATIC ENFORCEMENT):** The system AUTOMATICALLY sells any position whose value falls below 10% of total portfolio equity. If a partial sell leaves a position below this threshold (e.g., selling some shares leaves only $800 in a $10,000 portfolio), the remainder is automatically liquidated. The LLM does NOT need to call a tool - this happens automatically after trade execution and is recorded in the trade history.
- **Dynamic Fallbacks:**
    - If `allocation_percentage` is missing, the system defaults to **5%** (then applies the $1,000 bump logic).

## 5b. Automatic Dust Position Cleanup
After EVERY trade execution (BUY or SELL), the engine performs an automatic post-trade check to prevent small positions from polluting the portfolio:

1. **Threshold Check:** Scans all remaining positions and calculates their current market value
2. **10% Rule:** Compares each position's value against 10% of total portfolio equity
3. **Automatic Sale:** Any position below the threshold is automatically sold in full
4. **Trade Ledger:** Each dust cleanup sale is recorded in the `trades` table with:
   - `signal`: "SELL"
   - `decision_id`: NULL (system-generated, not from LLM)
   - `reasoning`: "Automatic dust position cleanup: Position value below 10% of portfolio equity"
   - Proper P&L calculations (realized gain/loss)
5. **Portfolio Updates:** Cash, SMA, and metrics are updated to reflect the dust sale
6. **LLM Notification:** The cleanup is logged in the trade history, so the LLM can see what happened in the "Recently Executed Trades" section of their portfolio context

**Example Scenario:**
- Portfolio Equity: $10,000 (10% threshold = $1,000)
- Agent owns 20 shares of XYZ @ $125 = $2,500 position
- Agent sells 15 shares @ $125 = $1,875 (using `sell_75_percent` tool)
- Remaining position: 5 shares @ $125 = $625 (below $1,000 threshold)
- Post-trade cleanup detects $625 < $1,000 threshold
- System automatically sells remaining 5 XYZ shares @ $125 = $625
- Both trades recorded with full audit trail
- LLM sees both sales in their trade history

**Implementation:** `apps/engine/execution/portfolio.py` → `_check_and_sell_dust_positions()`

## 5c. Available Sell Tools
The system provides the following sell calculation tools for agents:
- `sell_10_percent`: Calculate 10% of position (small profit-taking)
- `sell_25_percent`: Calculate 25% of position (partial exit)
- `sell_33_percent`: Calculate 33% of position (one-third exit)
- `sell_50_percent`: Calculate 50% of position (half exit)
- `sell_75_percent`: Calculate 75% of position (majority exit)
- `sell_100_percent`: Calculate 100% of position (full exit)

**Note:** The system does NOT require a tool call for dust cleanup - it happens automatically.

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
