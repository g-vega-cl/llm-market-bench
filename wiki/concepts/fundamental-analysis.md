---
tags: [fundamental-analysis, key-metrics, tools, fmp, yfinance]
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
- **YFinanceProvider**: Retrieves corresponding metrics from Yahoo Finance's `Ticker.info` object and normalizes the fields to match the FMP schema (including percentage conversions, e.g., normalizing Debt-to-Equity ratios).

Standardized fields returned to the models include:
- Valuation: `peRatio`, `priceToSalesRatio`, `pbRatio`, `enterpriseValueOverEBITDA`
- Leverage & Liquidity: `debtToEquity`, `currentRatio`
- Profitability & Returns: `roe` (Return on Equity), `dividendYield`, `freeCashFlowYield`
- Per-Share Metrics: `bookValuePerShare`, `revenuePerShare`, `netIncomePerShare`, `freeCashFlowPerShare`

## Volume & Liquidity Analysis

To assist trading agents in identifying accumulation, exhaustion, and liquidity dynamics, the system leverages raw daily trading volume from the `FinancialProvider`. 

Instead of requiring agents to calculate volume derivatives manually, the `get_price_history` tool is enhanced to automatically output daily volume alongside historical prices, and automatically append computed **Volume Context** metrics. This includes:
- **Average Daily Volume (ADV)**: Baseline average calculated dynamically (up to 20 days lookback).
- **Relative Volume (RVOL)**: Expressed as a multiplier (e.g., "2.3x above 20-day average") and a historical percentile ranking to clearly signal unusual volume spikes.

## Related

- [[entities/engine]]
- [[entities/pipeline]]
- [[concepts/tool-enforcement]]
