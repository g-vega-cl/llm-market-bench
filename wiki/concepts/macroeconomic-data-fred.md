---
tags: [macro, fred, economic-indicators, tools, newsletter, autoresearch]
category: concept
---

# FRED Macroeconomic Data Integration

The Federal Reserve Economic Data (FRED) integration provides official macroeconomic time series data to the engine. It powers both pull-based LLM agent tool calling (`get_macro_economic_series`) and pre-fetched structured macroeconomic context for automated newsletter generation (`generate_daily_newsletter`).

## Architecture & Data Flow

```
[Agent Tool / Newsletter Generator]
                │
                ▼
      [core.fred Module]
    (Alias Resolution & Cache Check)
       │                    │
  (Cache Hit)          (Cache Miss)
       │                    ▼
       │            [FRED HTTP API]
       │                    │
       │                    ▼
       │          [Upsert Supabase Cache]
       │          (`fred_series_cache`)
       ▼                    ▼
   [Formatted Markdown / Structured Series Data]
```

## Curated Indicator Packs & Aliases

The system maps convenient high-level alias keys to official FRED series identifiers across four macroeconomic categories:

| Pack | Alias | Series ID | Description | Default Units |
| :--- | :--- | :--- | :--- | :--- |
| **Core Benchmarks** | `fed_funds`<br>`treasury_10y`<br>`treasury_2y`<br>`yield_curve_10y2y`<br>`cpi`<br>`core_cpi`<br>`unemployment`<br>`high_yield_spread` | `FEDFUNDS`<br>`DGS10`<br>`DGS2`<br>`T10Y2Y`<br>`CPIAUCSL`<br>`CPILFESL`<br>`UNRATE`<br>`BAMLH0A0HYM2` | Fed Funds Rate<br>10Y Constant Maturity Yield<br>2Y Constant Maturity Yield<br>10Y-2Y Spread (Inversion Monitor)<br>Headline CPI YoY<br>Core CPI YoY<br>Unemployment Rate<br>High-Yield Credit Spread | `lin`<br>`lin`<br>`lin`<br>`lin`<br>`pc1`<br>`pc1`<br>`lin`<br>`lin` |
| **Liquidity & Money** | `m2`<br>`fed_balance_sheet`<br>`reverse_repo` | `M2SL`<br>`WALCL`<br>`RRPONTSYD` | M2 Money Supply YoY<br>Fed Total Assets<br>Overnight Reverse Repo | `pc1`<br>`lin`<br>`lin` |
| **Growth & Labor** | `nonfarm_payrolls`<br>`initial_claims`<br>`real_gdp`<br>`retail_sales` | `PAYEMS`<br>`ICSA`<br>`GDPC1`<br>`RSAFS` | Total Nonfarm Payrolls Change<br>Initial Jobless Claims<br>Real GDP Growth YoY<br>Advance Retail Sales YoY | `chg`<br>`lin`<br>`pc1`<br>`pc1` |
| **Inflation & Sentiment** | `pce`<br>`consumer_sentiment`<br>`breakeven_5y`<br>`breakeven_10y` | `PCEPI`<br>`UMCSENT`<br>`T5YIE`<br>`T10YIE` | PCE Inflation YoY<br>UMich Consumer Sentiment<br>5Y Breakeven Inflation<br>10Y Breakeven Inflation | `pc1`<br>`lin`<br>`lin`<br>`lin` |

*Arbitrary raw FRED series IDs (e.g. `WALCL`, `PCEPI`) are also supported directly.*

## Caching Strategy

- **Table**: `fred_series_cache` in PostgreSQL (Supabase).
- **TTL**: Configured via `FRED_CACHE_TTL_HOURS` (default: 12 hours).
- **Resilience**: If the external FRED API is unavailable or `FRED_API_KEY` is not present, stale cached records are served as fallback data without failing the trading agent or newsletter synthesis.

## Usage Surfaces

1. **LLM Trading Agents & Meta-Researcher**:
   - Tool `get_macro_economic_series` registered in `CANONICAL_TOOLS_REGISTRY` and selectable in `PromptResearchResult.selected_tools`.
2. **Daily Generated Newsletter**:
   - `generate_daily_newsletter` pre-fetches `get_curated_macro_dashboard()` to populate real-time rate, yield spread, and inflation figures into Section 1 (`### 🌐 The Macro & Cross-Asset Narrative`).

## Related

- [[entities/autoresearch]]
- [[entities/generated-newsletters]]
- [[concepts/fundamental-analysis]]
