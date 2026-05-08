---
tags: [source, web, portfolios, ui]
category: source
source: docs/web/portfolios-ui.md
---

# Source: Portfolios UI

Implementation of the Portfolios section — summary list + detail view per agent.

Key details:

- **Summary page** (`/portfolios`): Cards for each agent, separated into Active vs Retired by matching `owner_id` against `models.json`
- **Detail page** (`/portfolios/$portfolioId`): Header, equity curve (D3-based with benchmark overlay), positions table (sortable + expandable), recent trades
- **Equity curve**: D3.js SVG rendering with gradient fill, crosshair, inline data display, benchmark comparison (S&P 500, Nasdaq, etc.), percentage normalization mode
- **Sortable positions**: Client-side sort on Invested, % of Portfolio, P&L USD, P&L % — `useState` + `useMemo`
- **Thinking Process**: Expandable reasoning per position/trade, multi-strategy matching (direct link → proximity → fallback by ticker), machine-auditable trail
- **Benchmark data**: Fetched from `price_history` table, date-deduplicated (keeps last price per day)
- **Owner ID normalization**: lowercased, spaces/underscores → dashes, trimmed — handles formatting variations
- **Mobile responsive**: scaled padding, fonts, short column headers, horizontal scroll for tables
