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
- **Server-side dedup RPC (2026-06-01)**: The web app's homepage `fetchTodayData` fetches price history via the `latest_per_ticker_per_day(p_tickers, p_days)` SQL function (migration `supabase/migrations/20260601000000_add_latest_per_ticker_per_day_rpc.sql`) instead of pulling raw rows. The RPC uses `DISTINCT ON (ticker, (fetched_at AT TIME ZONE 'America/New_York')::date)` to return at most one row per (ticker, ET calendar day) and the frontend's `buildHistoryGroup` runs as a no-op. See [[concepts/hero-loader-split]] for the full pattern.

## Frontend Integration & Yield Rules

The exact same 23 tickers and volatility calculations are mirrored on the Web App Dashboard Today page:
- **Inverse Bond Yields Rule**: Explains the inverse price-to-yield mechanics of `IEF` (7-10 Year Treasury) and `TLT` (20+ Year Treasury) ETF prices to actual interest yields (price drop = rising yields; price rise = falling yields).
- **Prompt Parity**: Because the Python engine injects this exact same macro block into every LLM agent's prompt during decision cycles (via the `{macro_context}` slot in `prompts.py`), there is 100% parity between what the user sees on the dashboard and what the AI models analyze when determining trade triggers.

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

