---
tags: [fundamental-analysis, key-metrics, tools, fmp, yfinance, earnings, market-barometer]
category: concept
---

# Fundamental Financial Analysis & Key Metrics

A design pattern introducing structured fundamental key metrics to LLM models to aid trading thesis verification.

## Tradeoff: Full Filings vs. Key Metrics

Trading algorithms often benefit from corporate filing data (e.g. SEC 10-K, 10-Q, 8-K) to make high-conviction decisions. However, raw filing documents are extremely verbose, easily spanning hundreds of thousands of tokens, which leads to:
1. **Context Bloat**: Sapping prompt space and increasing model costs.
2. **Attention Dilution**: Degrading target recall for core newsletter signals ("lost in the middle" effect).
3. **Execution Latency**: Slowing down tool loop iterations.

To resolve this tradeoff, the platform implements **Structured Key Metrics Extraction**. Rather than feeding raw filing text to models, the `get_key_metrics` tool retrieves standardized metrics (such as P/E, PEG, Debt-to-Equity, ROE, free cash flow yields, book value, etc.) derived from those filings.

## Integration & Providers

The tool delegates to the active `FinancialProvider` through the `MarketDataManager`:
- **FMPProvider**: Fetches real-time structured key metrics from the FMP `/key-metrics/{symbol}` endpoint. It supports annual or quarterly periods and limits to minimize token count.

> [!WARNING]
> **yfinance Provider Deprecation**: The `YFinanceProvider` is deprecated and has been completely removed from the codebase. It must not be used to fetch market or fundamental data due to severe reliability concerns and Yahoo Finance scraping/rate-limiting restrictions. The factory raises a `ValueError` if a fallback to `yfinance` is requested. FMP (`FMPProvider`) is the sole active financial provider for these metrics.

Standardized fields returned to the models include:
- Valuation: `peRatio`, `priceToSalesRatio`, `pbRatio`, `bookToMarketRatio` (computed as `1 / pbRatio`), `enterpriseValueOverEBITDA`, `priceToFreeCashFlowsRatio`
- Leverage & Liquidity: `debtToEquity`, `currentRatio`, `netDebt`, `marketCap`, `enterpriseValue`
- Profitability & Returns: `roe` (Return on Equity), `dividendYield`, `freeCashFlowYield`
- Per-Share Metrics: `bookValuePerShare`, `revenuePerShare`, `netIncomePerShare`, `freeCashFlowPerShare`
- Current Derived Valuation (summary output via `get_key_metrics` tool):
  - **Forward P/E**: Calculated as $\text{Current Price} / \text{Next FY Estimated EPS}$ based on forward analyst estimates.
  - **CAPE (Cyclically Adjusted P/E)**: Calculated as $\text{Current Price} / \text{Average Historical EPS}$ over the last 10 annual periods (minimum 3 years required).


## Valuation Audit Tool (`audit_financial_valuation`)

To verify stock trades against intrinsic value without in-context mathematical hallucinations, the platform features a server-side **Valuation Audit Tool**. When called with a `ticker`, it:
1. Retrieves historical growth rates via FMP `/financial-growth` and consensus projections via FMP `/analyst-estimates`.
2. Computes the company's Weighted Average Cost of Capital (WACC) using the Capital Asset Pricing Model (CAPM) and weight factors.
3. Formulates a 5-year discounted Free Cash Flow (FCF) schedule under a mid-year convention.
4. Generates an EV-to-Equity Bridge, outputting the final implied price per share and comparing trailing multiples against index averages to audit valuation premium/discount.

### Quarterly-First Metric Retrieval

The audit tool requests `period="quarter", limit=2` first so that tickers with imminent earnings (e.g., MU reporting this week) receive the most recent quarterly data. The `FMPProvider.get_key_metrics` path automatically falls back to `period="annual"` when the stable `/key-metrics` and `/ratios` endpoints return `402 Payment Required` (a known constraint on certain FMP plan tiers).

When the audit tool detects that it received annual data (the returned `period` field doesn't contain `Q`), it surfaces an inline note in the report:

> ⚠️ NOTE: FMP quarterly metrics unavailable on current plan (402 Payment Required). DCF using annual fallback metrics; earnings-week signals should be discounted accordingly.

This surfaces the degradation so the verifier can discount short-term catalysts appropriately instead of silently using stale annual data.

### Barometer Premium/Discount Computation

The valuation tool queries `market_barometer_history` for the latest cap-weighted S&P 500 aggregates and uses them as the baseline for premium/discount computation. Two key columns are read:
- `pe_ratio` — S&P 500 trailing P/E baseline (default fallback: `22.5`)
- `pfcf_ratio` — S&P 500 Price-to-FCF baseline (default fallback: `20.0`)

The `pfcf_ratio` column was added by migration `20260621100000_add_pfcf_to_barometer.sql`. If the query fails (column drift, network error, etc.), the tool logs a `WARNING` so the degradation is visible in production rather than silently masking it via `except: pass`.

## Volume & Liquidity Analysis

To assist trading agents in identifying accumulation, exhaustion, and liquidity dynamics, the system leverages raw daily trading volume from the `FinancialProvider`. 

Instead of requiring agents to calculate volume derivatives manually, the `get_price_history` tool is enhanced to automatically output daily volume alongside historical prices, and automatically append computed **Volume Context** metrics. This includes:
- **Average Daily Volume (ADV)**: Baseline average calculated dynamically (up to 20 days lookback).
- **Relative Volume (RVOL)**: Expressed as a multiplier (e.g., "2.3x above 20-day average") and a historical percentile ranking to clearly signal unusual volume spikes.

## S&P 500 Market Health Barometer

To track broader economic health and market valuation regimes, the system implements a daily **S&P 500 Market Health Barometer**. 

A daily background script (`update_market_barometer.py`) gathers fundamental and pricing data for S&P 500 constituents (falling back to a curated top-100 list representing ~80% of S&P 500 cap to stay under FMP rate limits). It computes cap-weighted index aggregates:
- **Aggregate Trailing P/E**: $\frac{\sum \text{Market Cap}}{\sum \text{Net Income}}$
- **Aggregate Forward P/E**: $\frac{\sum \text{Market Cap}}{\sum \text{Estimated Net Income}}$
- **Aggregate P/S (Price-to-Sales)**: $\frac{\sum \text{Market Cap}}{\sum \text{Revenue}}$ (a distortion-free metric that includes loss-making companies)
- **Aggregate P/B (Price-to-Book)**: $\frac{\sum \text{Market Cap}}{\sum \text{Book Value}}$
- **Aggregate Price-to-FCF**: $\frac{\sum \text{Market Cap}}{\sum \text{Free Cash Flow}}$ (mathematically computed from FCF yields, excluding companies with negative or zero free cash flow to avoid skewing valuation metrics)
- **Earnings Beat Rate**: Percentage of constituents whose most recent earnings report exceeded estimates.

These daily snapshots are saved to `market_barometer_history` in Supabase. The latest snapshot is injected into the system prompt's global macroeconomic context (`macro_context`), the LLMs can call `get_market_health_barometer` to check historical valuation trends, and the metrics are displayed to users in a premium glassmorphism card on the dashboard [HomePage](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/home/pages/HomePage.tsx) (visualizing trailing/forward multiples and an animated earnings surprise beat rate progress bar).

## Company Earnings & Calendar

To aid event-driven thesis verification (e.g. trading around quarterly announcements), the `get_earnings_history` tool fetches:
1. **Upcoming Earnings Announcement**: Estimated date, expected EPS, and expected revenue.
2. **Historical Earnings Reports**: Recent actual vs. estimated EPS and revenue, surprise absolute/percentage numbers, and beat/miss status.

The tool delegates to:
- **FMPProvider**: Queries `/stable/earnings?symbol={ticker}`.

## Related

- [[entities/engine]]
- [[entities/pipeline]]
- [[concepts/tool-enforcement]]

