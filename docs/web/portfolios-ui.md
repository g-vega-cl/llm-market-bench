# Portfolios UI

This document describes the implementation of the Portfolios section in the AI Wall Street frontend.

## 1. Overview
The Portfolios section allows users to monitor the performance and holdings of each AI trading agent. It provides both a high-level summary of all agents and a detailed view for each individual agent.

## 2. Pages

### Portfolios Summary (`/portfolios`)
- **Route**: `apps/web/src/routes/portfolios/index.tsx`
- **Description**: Displays a list of all AI agent portfolios, separated into **Active** and **Retired** sections.
- **Active vs Retired Classification**:
  - Portfolios are classified based on their `owner_id` field
  - **Active**: `owner_id` matches a model name in the current `packages/config/models.json` configuration
  - **Retired**: `owner_id` does not match any current model (e.g., outdated models like `gemini-3-flash-preview`, `mimo-v2-pro`)
  - Owner ID normalization handles formatting variations (spaces, dashes, underscores, case) for robust matching
- **Key Metrics** (for each portfolio card):
    - Total Equity (Net Liquidation Value)
    - Cash Balance
    - Buying Power
- **Interaction**: Clicking an agent card navigates to their specific portfolio detail page.
- **Visual Distinction**:
  - Active portfolios: White background, green "Active" badge, full opacity
  - Retired portfolios: Gray background, gray "Retired" badge, reduced opacity (60%)

### Portfolio Detail (`/portfolios/$portfolioId`)
- **Route**: `apps/web/src/routes/portfolios/$portfolioId.tsx`
- **Description**: Provides an in-depth analysis of a specific agent's portfolio.
- **Sections**:
    - **Header**: Shows the agent's name, total equity, and current cash balance.
    - **Performance Timeline**: A D3-based line chart (Equity Curve) showing the daily progress of the portfolio's total equity.
    - **Current Positions**: A table listing all stocks currently held by the agent. Displays quantity, average cost, current price, **Invested Amount**, **% of Portfolio**, and P&L. Rows are interactive; clicking an entry expands to show the AI's reasoning.
    - **Recent Trades**: A historical ledger of the agent's executions. Like the positions table, trade rows expand to reveal the specific reasoning behind the BUY or SELL signal.

## 3. Data Visualization: Equity Curve
The performance chart is built using **D3.js** to ensure maximum flexibility and alignment with the project's "no new charting libraries" constraint.

- **Component**: `apps/web/src/routes/portfolios/components/-PerformanceChart.tsx`
- **Features**:
    - Responsive SVG rendering.
    - Time-series x-axis based on daily performance snapshots.
    - Linear y-axis with formatted currency labels.
    - Gradient area fill under the equity line for better visual depth.
    - Automated gridlines and axes using D3 primitives.
    
## 4. Interactive Reasoning (Thinking Process)
One of the core features of the Portfolio Detail page is the **Thinking Process** expansion. 

- **Logic**: Each position or trade row in the table can be toggled to expand a detailed reasoning block.
- **Data Fetching (Positions)**: Joins the `position_pnl` data with the latest signals from the `decisions` table.
- **Data Fetching (Trades)**: The `fetchTrades` function uses a multi-strategy matching engine to ensure reasoning is found even if explicit ID links are missing.
- **Matching Strategies**:
    1. **Direct Link**: Match by `trade_id` or `decision_id` pointers.
    2. **Proximity**: Match by **Ticker + Signal + Time window** (finding decisions within 24 hours of execution).
    3. **Fallback**: Match by the most recent relevant ticker signal.
- **User Experience**: Provides transparency into *why* an agent made a specific trade, fulfilling the machine-auditable trail objective of the platform.

## 4. Data Sources

### Portfolios Table
The summary page and header information are fetched from the `portfolios` table, which contains the latest calculated Reg T metrics for each agent.

### Portfolio Performance Table
The equity curve is powered by the `portfolio_performance` table. This table stores daily snapshots of each portfolio's metrics, recorded at the end of each trading session by the backend engine.

### Position P&L View
The positions table utilizes the `position_pnl` SQL view. This view dynamically joins `portfolio_positions` with `market_data_cache` to provide real-time (or near real-time) unrealized profit and loss calculations.
- **Augmentation**: In the `-queries.ts` layer, this data is further augmented by joining with the `decisions` table to retrieve requested `reasoning` text.
- `unrealized_pnl_usd`: `(current_price - cost_basis) * quantity`
- `unrealized_pnl_pct`: `((current_price / cost_basis) - 1) * 100`

### New Portfolio Metrics
These metrics are calculated client-side in the `PositionsTable` component to provide immediate context on allocation and weight:
- **Invested (Cash)**: `quantity * average_cost_basis` (Total capital deployed in the position).
- **% of Portfolio**: `(Position Invested Cash / Total Portfolio Invested Cash) * 100` (The weight of the stock relative to the total cash invested across all active positions).


## 5. Implementation Details

### Server Functions
Data fetching is handled by TanStack Start server functions located in `apps/web/src/routes/portfolios/-queries.ts`. This ensures that sensitive database queries remain on the server and are delivered to the frontend in a type-safe manner.

### Portfolio Configuration
- **File**: `apps/web/src/routes/portfolios/-config.ts`
- **Purpose**: Loads and caches the list of active owner IDs from `packages/config/models.json`
- **Function**: `getActiveOwnerIds()` returns normalized model names for portfolio classification
- **Error Handling**: Falls back to empty array if models.json fails to load (marks all portfolios as retired)

### Owner ID Normalization
- **File**: `apps/web/src/routes/portfolios/-queries.ts`
- **Function**: `normalizeOwnerId(ownerId: string | null): string`
- **Purpose**: Ensures consistent comparison of owner IDs regardless of formatting
- **Normalization Rules**:
  - Converts to lowercase
  - Replaces spaces, underscores, and multiple dashes with single dashes
  - Trims leading/trailing dashes
- **Example**: `"Gemini_3_Flash_Preview"` → `"gemini-3-flash-preview"`

### Styling
All pages use **Tailwind CSS** and follow the project's **Zinc** color palette to maintain consistency with the rest of the application.

---
[[back to Overview](../Overview.md)]
