# Portfolios UI

This document describes the implementation of the Portfolios section in the AI Wall Street frontend.

## 1. Overview
The Portfolios section allows users to monitor the performance and holdings of each AI trading agent. It provides both a high-level summary of all agents and a detailed view for each individual agent.

## 2. Pages

### Portfolios Summary (`/portfolios`)
- **Route**: `apps/web/src/routes/portfolios/index.tsx`
- **Description**: Displays a list of all active AI agents as cards.
- **Key Metrics**:
    - Total Equity (Net Liquidation Value)
    - Cash Balance
    - Buying Power
- **Interaction**: Clicking an agent card navigates to their specific portfolio detail page.

### Portfolio Detail (`/portfolios/$portfolioId`)
- **Route**: `apps/web/src/routes/portfolios/$portfolioId.tsx`
- **Description**: Provides an in-depth analysis of a specific agent's portfolio.
- **Sections**:
    - **Header**: Shows the agent's name, total equity, and current cash balance.
    - **Performance Timeline**: A D3-based line chart (Equity Curve) showing the daily progress of the portfolio's total equity.
    - **Current Positions**: A table listing all stocks currently held by the agent.

## 3. Data Visualization: Equity Curve
The performance chart is built using **D3.js** to ensure maximum flexibility and alignment with the project's "no new charting libraries" constraint.

- **Component**: `apps/web/src/routes/portfolios/components/-PerformanceChart.tsx`
- **Features**:
    - Responsive SVG rendering.
    - Time-series x-axis based on daily performance snapshots.
    - Linear y-axis with formatted currency labels.
    - Gradient area fill under the equity line for better visual depth.
    - Automated gridlines and axes using D3 primitives.

## 4. Data Sources

### Portfolios Table
The summary page and header information are fetched from the `portfolios` table, which contains the latest calculated Reg T metrics for each agent.

### Portfolio Performance Table
The equity curve is powered by the `portfolio_performance` table. This table stores daily snapshots of each portfolio's metrics, recorded at the end of each trading session by the backend engine.

### Position P&L View
The positions table utilizes the `position_pnl` SQL view. This view dynamically joins `portfolio_positions` with `market_data_cache` to provide real-time (or near real-time) unrealized profit and loss calculations:
- `unrealized_pnl_usd`: `(current_price - cost_basis) * quantity`
- `unrealized_pnl_pct`: `((current_price / cost_basis) - 1) * 100`

## 5. Implementation Details

### Server Functions
Data fetching is handled by TanStack Start server functions located in `apps/web/src/routes/portfolios/-queries.ts`. This ensures that sensitive database queries remain on the server and are delivered to the frontend in a type-safe manner.

### Styling
All pages use **Tailwind CSS** and follow the project's **Zinc** color palette to maintain consistency with the rest of the application.

---
[[back to Overview](../Overview.md)]
