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
- `get_reference_quote(ticker, force_refresh=False, session="close", history=None, target_date=None)` — fetches regular session closing quote or pre-market reference quote with verified 1D price and percentage change vs prior trading day's close, preventing after-hours drift from corrupting daily performance metrics in evening synthesis pipelines.
- `is_market_open()`, `is_premarket()`, `is_trading_day(target_date)`, `get_market_holidays()` — session checks delegated to the session manager.
- `screen_stocks(...)` — provider screening with an in-memory screener cache keyed on the sorted parameter set.
- Provider passthroughs: `get_key_metrics`, `get_earnings_history`, `get_analyst_estimates`, `get_financial_growth`, `get_company_profile`.
- Technical indicator computation: `get_technical_indicators` (`apps/engine/tools/technicals.py`) computes RSI-14, MACD, 20D VWAP, SMA-20/50, RVOL, and 52-week range % with optional point-in-time `cutoff_date`.

The manager exposes `client`, `cache_ttl_seconds`, and `provider` as properties with setters, so overrides propagate into the underlying `MarketDataCache`. `_validate_date_coverage` remains as a backward-compatibility alias for `market_transforms.validate_date_coverage`.

`is_market_open()` and `get_market_holidays()` are thin delegations to `self.session` — the facade no longer copies caches or locks back and forth around the call. Shared state lives on `MarketSessionManager` and is reached through the lock proxy described below.

#### `get_reference_quote` — Session-Anchored Reference Pricing

`get_reference_quote(ticker, force_refresh=False, session="close", history=None, target_date=None)` returns a normalized quote dict (`price`, `previous_close`, `change`, `change_pct`, optional `volume`) whose 1D move is always measured against the prior trading day's close rather than an after-hours tick. It is the canonical quote accessor for evening synthesis pipelines (newsletter close briefing, FX context, multi-horizon reference matrix) where post-market drift would otherwise corrupt the reported daily performance.

The facade is a thin wrapper: it resolves the pre-market short-circuit and the live quote, then delegates all synthesis to the pure `compute_reference_quote` transform in `market_transforms.py`.

Resolution order:

1. **`session="open"` pre-market short-circuit** — when `is_premarket()` is true, a `get_premarket_quote(ticker)` result with a non-null price is returned directly. Any exception during the pre-market check is logged at debug level and ignored.
2. **Regular quote** — `get_quote(ticker, force_refresh=force_refresh)` supplies `price`, `previous_close`, `change`, and `change_pct`.
3. **History resolution** — when the caller supplies `history`, it is used as-is and no extra `get_history` call is made. Otherwise, history is fetched (`get_history(ticker, days=5)`) only when the quote is missing, has a non-positive price, or lacks `previous_close` / `change_pct`. A history fetch failure is logged at debug level and treated as no history.
4. **Synthesis** — `compute_reference_quote(quote=quote, history=hist, target_date=target_date)` derives the price, prior close, change, and percentage from the quote and/or bars, returning `None` when no valid positive price can be resolved.

Invalid input (empty or non-string ticker) returns `None`.

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

#### Event-Loop-Safe Lock Lifecycle

Both caches are guarded by class-level `asyncio.Lock` singletons (`_market_status_lock`, `_holidays_lock`) that prevent thundering-herd refetches. Because a lock created in one event loop cannot be awaited from another (it raises `RuntimeError: ... is bound to a different event loop`), the manager never instantiates them directly. Instead it resolves them through two classmethods:

- `_get_market_status_lock()` — returns `_market_status_lock`, recreating it when it is `None` or when its `_loop` attribute is bound to a different (or dead) event loop than `asyncio.get_running_loop()`.
- `_get_holidays_lock()` — same contract for the holidays lock.

`is_market_open()` and `get_market_holidays()` call the relevant accessor and then `async with lock:` for the double-checked cache refill. This makes the caches safe to share across the long-lived runner loop, short-lived CLI invocations, and per-test event loops without stale-lock deadlocks.

`MarketDataManager` mirrors both locks as class attributes through the `_LockProxy` descriptor, which transparently reads and writes the corresponding `MarketSessionManager` class attribute. Assigning `MarketDataManager._market_status_lock = None` (as tests do to reset state) therefore resets the session manager's lock too, and reading it always returns the live lock object rather than a stale copy.

### `market_transforms.py` — pure functions

Stateless helpers with no I/O:

- `validate_date_coverage(rows, days_requested)` — decides whether cached history is trustworthy: rejects all-today data, requires at least `ceil(days/2)` distinct dates, and rejects caches whose newest entry is more than 4 calendar days old.
- `compute_premarket_quote(quote, aftermarket_quote, history)` — synthesizes a standardized pre-market quote dict (`price`, `previous_close`, `change`, `change_pct`, optional `volume`), preferring a dedicated aftermarket quote, falling back to the standard quote, and using recent history for a missing previous close.
- `compute_reference_quote(quote, history=None, target_date=None)` — the session-anchored reference quote synthesizer behind `MarketDataManager.get_reference_quote`. It:
  - Normalizes history via `_sort_and_filter_history`, which drops bars with missing, non-numeric, `NaN`, or non-positive prices and sorts the remainder ascending by `date` / `fetched_at` / `timestamp` (so descending DB rows are handled correctly).
  - Pins the session prefix to `target_date[:10]` when supplied, otherwise today's UTC date. A `target_date` earlier than today marks the run as historical.
  - For live (non-historical) runs, prefers the real-time quote's `price`, `previous_close`, `change`, `change_pct`, and `volume` when the price is valid.
  - Falls back to `_derive_from_history`, which takes the last bar at or before the target prefix as the session price and volume.
  - Resolves the prior close via `_resolve_prior_close`, which selects the most recent bar strictly before the target prefix; when no such bar exists it uses the penultimate bar (or the full list when the last bar's close differs from the current price by more than `1e-4`).
  - Recomputes `change` / `change_pct` from `price - previous_close` when the percentage is missing, nulls out non-positive or `NaN` prior closes, and returns `None` when no valid positive price exists.
- `_extract_history_prev_close(history)` — resolves the prior trading day's close from a history list (retained as a standalone helper; `get_reference_quote` now resolves prior closes through `compute_reference_quote`).

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
- [[concepts/multi-horizon-reference]]
