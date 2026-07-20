---
tags: [engine, macro, tracking, regime]
category: entity
---

# Macro Tracker

The Global Macro Tracker at `apps/engine/core/macro_tracker.py` continuously
monitors key economic indicators and injects a "regime awareness" snapshot into
every LLM agent's context before trading decisions.

## How It Works

1. **Batch fetch**: All 23 macro tickers are quoted in a single batch call
2. **30-day history**: For each ticker, computes daily % returns and rolling volatility
3. **Regime flagging**: Flags movements as "Normal", "❗ UNUSUAL" (>1.5σ), or "⚠️ HIGHLY UNUSUAL" (>2σ)
4. **Context injection**: A `--- GLOBAL MACRO ENVIRONMENT ---` block is prepended to the user prompt

## Categories (23 tickers)

| Category | Tickers | Count |
|---|---|---|
| Equities | SPY (S&P 500), QQQ (Nasdaq 100), DIA (Dow Jones), IWM (Russell 2000) | 4 |
| International | EWJ (Japan), EWY (South Korea), VGK (Europe), MCHI (China), EEM (EM), EWU (UK), EWC (Canada), INDA (India) | 8 |
| Commodities | GLD (Gold), SLV (Silver), CPER (Copper), USO (Oil), UNG (Natural Gas) | 5 |
| Fixed Income | IEF (7-10yr Treasury), TLT (20+yr Treasury), TIP (TIPS/Inflation) | 3 |
| FX & Risk | UUP (USD Index), VIXY (Volatility) | 2 |
| Crypto | BTCUSD (Bitcoin) | 1 |

## Design Constraints

- **FMP-compatible only**: All tickers must work with Financial Modeling Prep API (no Yahoo-style `^VIX`, `DX-Y.NYB`)
- **ETF proxies**: Indices are tracked via ETFs (e.g., VIXY for VIX, UUP for DXY, IEF/TLT for yields)
- **Unique tickers only**: No duplicates across categories; batch fetch deduplicates implicitly

## Frontend Integration & Yield Rules

The exact same 23 tickers and volatility calculations are mirrored on the Web App Dashboard Today page:
- **Inverse Bond Yields Rule**: Explains the inverse price-to-yield mechanics of `IEF` (7-10 Year Treasury) and `TLT` (20+ Year Treasury) ETF prices to actual interest yields (price drop = rising yields; price rise = falling yields).
- **Prompt Parity**: Because the Python engine injects this exact same macro block into every LLM agent's prompt during decision cycles (via the `{macro_context}` slot in `prompts.py`), there is 100% parity between what the user sees on the dashboard and what the AI models analyze when determining trade triggers.

## Execution & Scheduling

The rolling volatility, percentage change, and regime classification metrics are pre-calculated using the `update_prices.py` script (`apps/engine/scripts/update_prices.py`) and cached in the `market_data_cache` table.

This is executed automatically on a scheduled **GitHub Action workflow** (`.github/workflows/update-prices.yml`) to keep the data fresh:

- **Cadence**: Scheduled to run **every 30 minutes** during US market hours:
  - **Cron Trigger**: `cron: "0,30 13-21 * * 1-5"` (13:00 - 21:00 UTC, covering both EDT 9:30 AM open and EST 9:30 AM open with pre-market failsafe skip).
  - Can also be triggered manually via a `workflow_dispatch` event on GitHub.
- **Ingestion Pipeline Sync**: In addition to the dedicated price updater, the primary daily ingestion and consensus pipeline workflow (`.github/workflows/ingest.yml`) triggers at **9:35 AM ET, 10:35 AM ET, 11:35 AM ET, and 2:00 PM ET** on trading days via dual UTC offset crons (`cron: "35 13,14,15,16 * * 1-5"` and `"0 18,19 * * 1-5"`). Pre-market runs outside market hours (e.g. 13:35 UTC in EST) are gracefully skipped by the engine's `is_market_open()` failsafe.

- **Cache Persistence**: The calculated statistics (rolling 30-day volatility `stdev_pct`, `today_pct_change`, `price`, `regime_flag`) are saved to the persistent Supabase `market_data_cache` table. This allows the serverless loader (`fetch-today-data.ts`) to retrieve all 23 tickers in a single consolidated database query in less than 5ms.

## History

- **2026-05-28**: Resolved the "Market" section percentage returns reporting discrepancy for pure EOD tickers like `TLT` and `IEF`. Fixed a caching bug where the DB cache validation (`_validate_date_coverage` in `market_data.py`) returned a false cache hit for EOD tickers due to `.limit(90)` spanning over 45 calendar dates. Implemented an explicit staleness check (>4 calendar days old) to reject frozen caches, added `force_refresh` support to `get_history()`, and updated `update_prices.py` to force-refresh benchmark histories on daily cron syncs. Fully backfilled the historic price database to the current date, ensuring correct dashboard computations.
- **2026-05-27**: Relocated `SPY`, `TLT` (representing Bond yields), `IWM`, and `VIXY` to a new dynamic `'Market'` tab displayed as the default view, removing the static Benchmark Heroes top row and moving `QQQ` into `'Equities'`. Fixed stale calculations (such as the -8.44% OIL/USO bug) by adding the 8 missing macro tickers (`EWY`, `MCHI`, `INDA`, `SLV`, `USO`, `IEF`, `UUP`, `VIXY`) to `update_prices.py` to keep their 90-day EOD history fresh daily. Also implemented robust date filtering (excluding today's ET date) and deduplication (keeping the latest price per unique calendar day) in the frontend `buildHistoryGroup` query layer to prevent intraday snapshots from polluting return calculations. Covered by new Vitest unit tests.
- **2026-05-13**: Expanded from 16 to 23 tickers and 4 to 6 categories.
  Added: Fixed Income (split from Yields & Indices), FX & Risk (split), Crypto (new).
  Added tickers: TLT, TIP, UNG, BTCUSD, EWU, EWC, INDA.
  Renamed "Yields & Indices" → "Fixed Income" + "FX & Risk" for clarity.

## Related

- [[entities/engine]]
- [[entities/web-app]]
- [[sources/correlation-matrix-source]]
- [[concepts/rag-strategy]]

