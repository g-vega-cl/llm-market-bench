---
tags: [web, dashboard, audit, fundamental]
category: entity
---

# Market Barometer Audit Page

A dedicated audit page (`/barometer-audit`) that provides full transparency into the S&P 500 Market Health Barometer calculations. It displays the methodology and cap‑weighted formulas, an interactive constituent-level data table, and historical date selection.

## Purpose

- Verify index aggregate values (Trailing P/E, Forward P/E, P/B, P/S, P/FCF, Earnings Beat Rate) against underlying constituent data
- Explore individual stock metrics (market cap, price, ratios, beat status) with search, sort, and filter controls
- Shareable, refreshable URLs via TanStack Start URL search params for reproducible audits

## Features

- **Constituent Table**: Renders up to 100 S&P 500 components with computed columns (Trailing P/E, Forward P/E from next EPS estimate, P/S, P/B, P/FCF, Earnings Beat, Actual EPS, Expected EPS, Revenue Beat, Actual Revenue, and Expected Revenue)
- **Client‑Side Filters**: Search by ticker or company name; dropdown filter by earnings beat status (all / beats / misses / no data)
- **Column Sorting**: Click any header to sort ascending/descending; default sort by market cap descending; all new EPS and Revenue columns are fully sortable
- **Methodology Card**: Explains the cap‑weighted aggregate formulas (Sum(MCap) / Sum(Net Income) etc.)
- **Empty State**: Graceful message when a historical snapshot lacks constituent-level data (pre‑2026‑06‑17 runs)

## Route & Data Flow

- **Route**: `/barometer-audit` (created via `createFileRoute` with `validateSearch` for optional `date` param)
- **Server Loader**: Uses `createServerFn` to call `fetchMarketBarometerDates` and `fetchMarketBarometerForDate` from `~/features/home/api/fetch-barometer`
- **Database Column**: Relies on the `constituents_data` JSONB column in `market_barometer_history` (added by migration `20260620000000_add_constituents_data_to_barometer.sql`)
- **Automation Schedule**: Updated daily via GitHub Actions ([update-barometer.yml](file:///Users/cesarvega/Documents/p-code/llm-market-bench/.github/workflows/update-barometer.yml)) every weekday at 21:00 UTC (5 PM EDT / 4 PM EST, after US market close).
- **API Rate Limit Resilience**: Uses a concurrency-limited HTTP fetcher utilizing a `Semaphore(4)` and exponential backoff retry. The semaphore is explicitly released during backoff sleeps (retry waits) to prevent queue deadlocks and guarantee that transient rate limits do not cause high-cap tickers (e.g. AAPL) to fail and save with missing (`-`) beat information.


## Related

- [[entities/web-app]] — dashboard host and route integration
- [[concepts/fundamental-analysis]] — S&P 500 barometer concept and tools
- [[entities/database]] — schema for `market_barometer_history`
