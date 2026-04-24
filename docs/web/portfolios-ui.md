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
    - **Performance Timeline**: A D3-based line chart (Equity Curve) showing the daily progress of the portfolio's total equity. Features an **inline data display** that shows the current/hovered point's data between the title and chart, with a vertical crosshair and dot marker for visual tracking when hovering.
        - **Benchmark Comparison**: Users can select a benchmark (S&P 500, Nasdaq 100, Total World, Gold, Euro Stoxx, Japan Nikkei, Emerging Markets, Russell 2000, Dow Jones) to overlay on the chart for performance comparison.
        - **Percentage Normalization**: When a benchmark is selected, the chart automatically switches to percentage returns view (day 1 = 0%), enabling direct comparison between portfolio and benchmark performance.
        - **Outperformance Display**: The inline display shows portfolio return %, benchmark return %, and the outperformance differential with color coding (green for positive, red for negative).
    - **Current Positions**: A table listing all stocks currently held by the agent. Displays quantity, average cost, current price, **Invested Amount**, **% of Portfolio**, and P&L (USD and %). 
        - **Sortable Columns**: Click any of the sortable column headers (Invested, % of Portfolio, P/L USD, P/L %) to toggle between ascending and descending order. Visual indicators (↑↓↕) show the current sort direction.
        - **Interactive Rows**: Rows are clickable; clicking an entry expands to show the AI's reasoning.
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
    - **Inline Data Display** (2026-04-15):
        - A card between the chart title and the chart displays the current/hovered data point.
        - Shows date, portfolio value (or % when benchmark selected), benchmark value, and outperformance.
        - Default state shows the latest data point.
        - Hovering updates the display with the hovered point's data.
        - No floating tooltip - all information is visible inline for better mobile experience.
        - Crosshair and dot marker still appear on hover for visual tracking.
    - **Benchmark Comparison** (2026-04-14):
        - Multi-line support for overlaying benchmark index performance.
        - Portfolio line: solid sky-500 color with gradient area fill.
        - Benchmark line: dashed amber color for visual distinction.
        - Percentage normalization when benchmark is selected (both lines normalized to 0% at day 1).
        - Color-coded legend identifying portfolio vs benchmark.
    - **Outperformance Display** (2026-04-14):
        - When benchmark is active, the inline display shows:
            - Portfolio return % (or $ value in absolute mode)
            - Benchmark return % (or $ value in absolute mode)
            - Outperformance differential with color coding (green for positive, red for negative)
    - **Implementation Details**:
        - Uses D3 bisector to find the closest data point to the mouse position.
        - Invisible overlay rect captures mouse events across the chart area.
        - React state manages hover data and inline display.
        - Crosshair and dot marker are updated via a separate `useEffect` hook for smooth animation.
    
## 4. Sortable Positions Table
The positions table includes client-side sorting functionality for better data exploration.

- **Component**: `apps/web/src/routes/portfolios/components/-PositionsTable.tsx`
- **Sortable Columns** (2026-04-02):
    - **Invested**: Sort by total capital deployed in the position (`quantity × average_cost_basis`).
    - **% of Portfolio**: Sort by the position's weight relative to total invested cash.
    - **P/L (USD)**: Sort by unrealized profit/loss in dollars.
    - **P/L (%)**: Sort by unrealized profit/loss percentage.
- **Features**:
    - Click any sortable column header to toggle between ascending and descending order.
    - Visual indicators show sort direction: `↕` (unsorted), `↑` (ascending), `↓` (descending).
    - Default state is unsorted (positions appear in original order from the database).
    - Sort state persists while expanding/collapsing individual position details.
- **Implementation Details**:
    - Uses React `useState` to track current sort key and direction.
    - `useMemo` hook efficiently re-sorts positions only when dependencies change.
    - Sort calculations are performed client-side for instant response.
    - Total invested cash is recalculated on each render to ensure accurate portfolio percentages.

## 5. Interactive Reasoning (Thinking Process)
One of the core features of the Portfolio Detail page is the **Thinking Process** expansion. 

- **Logic**: Each position or trade row in the table can be toggled to expand a detailed reasoning block.
- **Data Fetching (Positions)**: Joins the `position_pnl` data with the latest signals from the `decisions` table.
- **Data Fetching (Trades)**: The `fetchTrades` function uses a multi-strategy matching engine to ensure reasoning is found even if explicit ID links are missing.
- **Matching Strategies**:
    1. **Direct Link**: Match by `trade_id` or `decision_id` pointers.
    2. **Proximity**: Match by **Ticker + Signal + Time window** (finding decisions within 24 hours of execution).
    3. **Fallback**: Match by the most recent relevant ticker signal.
- **User Experience**: Provides transparency into *why* an agent made a specific trade, fulfilling the machine-auditable trail objective of the platform.

## 6. Data Sources

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

### Benchmark Data (price_history)
Benchmark index prices are fetched from the existing `price_history` table using the `fetchBenchmarkHistory` function. This enables portfolio-to-benchmark comparison without storing separate benchmark snapshots.

**Date Deduplication:** The `price_history` table stores timestamps, which can result in multiple price snapshots per calendar day. `fetchBenchmarkHistory` deduplicates by date string, keeping only the **last** (most recent) price for each day. This prevents duplicate x-values in the D3 chart, which would otherwise cause vertical line artifacts in the interpolated curve.

## 7. Implementation Details

### Benchmark Selector Component
- **File**: `apps/web/src/routes/portfolios/components/-BenchmarkSelector.tsx`
- **Purpose**: Dropdown component for selecting a benchmark index to compare against portfolio performance.
- **Available Benchmarks**:
  - S&P 500 (SPY) - US Large Cap
  - Nasdaq 100 (QQQ) - US Tech
  - Total World (URTH) - Global Equity
  - Gold (GLD) - Commodities
  - Euro Stoxx (VGK) - Europe
  - Japan Nikkei (EWJ) - Japan
  - Emerging Markets (EEM) - EM Equity
  - Russell 2000 (IWM) - US Small Cap
  - Dow Jones (DIA) - US Blue Chip
- **Integration**: Works with TanStack Query to fetch benchmark data on selection change.
- **Tests**: `apps/web/src/routes/portfolios/components/-BenchmarkSelector.test.tsx`

### Server Functions
Data fetching is handled by TanStack Start server functions located in `apps/web/src/routes/portfolios/-queries.ts`. This ensures that sensitive database queries remain on the server and are delivered to the frontend in a type-safe manner.

### Portfolio Configuration
- **File**: `apps/web/src/routes/portfolios/-config.ts`
- **Purpose**: Loads and caches the list of active owner IDs via the `@repo/config/models.json` monorepo workspace package. By importing it natively as a package, it avoids bundler resolution errors.
- **Function**: `getActiveOwnerIds()` returns normalized model names for portfolio classification
- **Error Handling**: Falls back to an empty array if the JSON fails to load (marks all portfolios as retired)

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

## 8. Mobile Responsiveness (2026-04-15)

The portfolio pages are optimized for mobile devices with the following improvements:

### Portfolio Detail Page (`$portfolioId.tsx`)
- **Padding**: Reduced from `px-6 md:px-12 py-12` to `px-4 sm:px-6 py-8 md:py-12` for smaller screens
- **Header**: Font size scales from `text-2xl` on mobile to `text-4xl` on desktop
- **Stats Card**: Padding and gap reduce on mobile (`p-3 md:p-4`, `gap-4 md:gap-8`)

### Performance Chart
- **Inline Display**: Data is shown in a card between title and chart, eliminating tooltip positioning issues on mobile
- **Crosshair**: Still appears on hover for visual tracking but no floating overlay

### Positions Table
- **Minimum Width**: `min-w-[800px]` ensures horizontal scroll on small screens
- **Responsive Padding**: Cell padding scales from `px-3 py-3 sm:px-6 py-4` for better mobile touch targets
- **Shorter Headers**: "Qty" instead of "Quantity", "%" instead of "% of Portfolio"

### Trades Table
- **Minimum Width**: `min-w-[700px]` ensures horizontal scroll on small screens
- **Responsive Padding**: Cell padding scales from `px-3 py-3 sm:px-6 py-4`
- **Shorter Headers**: "Qty" instead of "Quantity", "Price" instead of "Total"

---
[[back to Overview](../Overview.md)]
