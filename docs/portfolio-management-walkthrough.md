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
| **Maintenance Margin** | `0.25 * Market Value of Longs` | The minimum equity required to hold positions (25%). |
| **Excess Liquidity** | `Total Equity - Maintenance Margin` | How much "buffer" you have before a margin call. |
| **Buying Power** | `4 * Excess Liquidity` | The max amount of stock you can buy intraday (4:1 Leverage). |

*Implementation: `apps/engine/execution/portfolio.py`*

## 3. Persistent State (Database)
State is preserved in Supabase so agents "carry over" their positions to the next day.

### `portfolios` Table
One row per AI Model (e.g., `gpt-4o`).
- `cash_balance`: Starts at $10,000.
- `buying_power`: Updated daily based on open positions.
- `total_equity`: Real-time net worth.

### `portfolio_positions` Table
Tracks exact holdings.
- `ticker`: e.g., "NVDA"
- `quantity`: Number of shares.
- `average_cost_basis`: Weighted average price paid.

## 4. LLM Prompt Injection
Before the LLM analyzes news, we insert a snapshot of its financial health.

**System Prompt Addition:**
```text
### Current Portfolio Status:
Cash Balance: $10,000.00
Total Equity: $10,000.00
Buying Power: $40,000.00
Maintenance Margin: $0.00

Current Positions:
- None
```

## 5. Decision Making (Allocation %)
LLMs can now output an `allocation_percentage` (0-100%) in their JSON decision.
- **Example:** "Buy NVDA, Allocation: 10%"
- **Engine Logic:** Calculates `10% * Buying Power` and places an order for that dollar amount.

## 6. Verification
We verify this logic with 6 standard scenarios (see `account-buying-power-reg-t4-calculations.md`), ensuring the system correctly handles:
- Leverage (Borrowing)
- Margin Calls (Liquidation scenarios)
- Fresh Accounts ($10k Cash)
