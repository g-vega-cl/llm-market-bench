---
tags: [market-data, execution, caching, providers, market-hours]
category: entity
---

# Market Data Subsystem

The market data subsystem (`apps/engine/execution/`) is the layer that supplies prices, historical bars, and market-session state to the rest of the pipeline. It coordinates external financial providers, a Supabase-backed persistent cache, US equity session schedules, and pure data transforms behind a single facade: `MarketDataManager`.

The subsystem was decomposed into vertical modules so that caching, session logic, and transforms can evolve and be tested independently.

## Modules

### `market_data.py` — `MarketDataManager` (facade)

The public entry point used by the pipeline. It wires together the cache, session manager, and provider, and exposes the high-level retrieval API:

- `get_quote(ticker, force_refresh=False)` — single quote with cache-first lookup, provider fetch with backoff, and a last-known-price fallback.
- `get_quotes(tickers, force_refresh=False)` — batch retrieval: cache batch → provider batch → individual pass for anything still missing.
- `get_history(ticker, days=14, force_refresh=False)` — historical bars, local DB first, then provider.
- `get_premarket_quote(ticker)` — synthesizes a pre-market quote from aftermarket data, standard quotes, and history fallback.
- `is_market_open()`, `is_premarket()`, `is_trading_day(target_date)`, `get_market_holidays()` — session checks delegated to the session manager.
- `screen_stocks(...)` — provider screening with an in-memory screener cache keyed on the sorted parameter set.
- Provider passthroughs: `get_key_metrics`, `get_earnings_history`, `get_analyst_estimates`, `get_financial_growth`, `get_company_profile`.

The manager exposes `client`, `cache_ttl_seconds`, and `provider` as properties with setters, so overrides propagate into the underlying `MarketDataCache`. `_validate_date_coverage` remains as a backward-compatibility alias for `market_transforms.validate_date_coverage`.

### `market_cache.py` — `MarketDataCache`

Database-backed persistence layer. It owns all Supabase reads/writes for market data:

- **Live quotes** in `market_data_cache`, TTL-aware (`MARKET_DATA_CACHE_TTL_SECONDS`). `get_quote` / `get_quotes_batch` return only fresh rows; `save_quote` / `save_quotes_batch` upsert, skipping NaN prices and deriving `today_pct_change` from `change_pct` or `previous_close`.
- **Historical bars** in `price_history`. `get_history` returns OHLCV rows only when coverage passes validation; `save_history` batch-upserts on `(ticker, fetched_at)`, defaulting `close` to `price` for EOD bars.
- **Last-known price** via `get_last_known_price`, which rejects entries older than 24 hours.

### `market_session.py` — `MarketSessionManager`

US equity session, calendar, and trading-hours logic with in-memory locking and caching:

- `is_market_open()` — FMP `exchange-market-hours` (NASDAQ) as the primary source, with a time-based override during the 9:30–9:50 AM ET open buffer on weekdays, and a Mon–Fri 09:30–16:00 ET fallback. Results cached for 30 minutes.
- `get_market_holidays()` — FMP `holidays-by-exchange`, cached for 24 hours.
- `is_trading_day(target_date)` — weekend check, FMP holiday check, then a rule-based holiday fallback.
- `is_known_us_market_holiday_fallback(date)` — static rule set covering New Year's, MLK, Presidents', Memorial, Juneteenth, Independence, Labor, Thanksgiving, and Christmas with observed-date handling.
- `is_premarket()` — Mon–Fri 04:00–09:30 ET.

### `market_transforms.py` — pure functions

Stateless helpers with no I/O:

- `validate_date_coverage(rows, days_requested)` — decides whether cached history is trustworthy: rejects all-today data, requires at least `ceil(days/2)` distinct dates, and rejects caches whose newest entry is more than 4 calendar days old.
- `compute_premarket_quote(quote, aftermarket_quote, history)` — synthesizes a standardized pre-market quote dict (`price`, `previous_close`, `change`, `change_pct`, optional `volume`), preferring a dedicated aftermarket quote, falling back to the standard quote, and using recent history for a missing previous close.

## Retrieval Flow

1. **Cache** — fresh rows from `market_data_cache` are returned immediately.
2. **Provider** — misses are fetched from the configured `FinancialProvider` with exponential backoff (`MARKET_DATA_RETRIES`).
3. **Fallback** — if all online retrieval fails, the last known price from `price_history` is used, provided it is under 24 hours old.

## Related

- [[entities/engine]]
- [[entities/pipeline]]
- [[concepts/execution]]
- [[concepts/vertical-slice-islands]]
- [[concepts/ingestion]]
