---
tags: [market-data, execution, caching, providers, market-hours]
category: entity
---

# Market Data Subsystem

The market data subsystem (`apps/engine/execution/`) is the layer that supplies prices, historical bars, and market-session state to the rest of the pipeline. It coordinates external financial providers, a Supabase-backed persistent cache, US equity session schedules, and pure data transforms behind a single facade: `MarketDataManager`.

The subsystem was decomposed into vertical modules so that caching, session logic, and transforms can evolve and be tested independently.

## Modules

### `market_data.py` — `MarketDataManager` (facade)

The public entry point used by the pipeline. It wires together the cache and provider, and exposes the high-level retrieval API:

- `get_quote(ticker, force_refresh=False)` — single quote with cache-first lookup, provider fetch with backoff, and a last-known-price fallback.
- `get_quotes(tickers, force_refresh=False)` — batch retrieval: cache batch → provider batch → individual pass for anything still missing.
- `get_history(ticker, days=14, force_refresh=False)` — historical bars, local DB first, then provider.
- `get_premarket_quote(ticker)` — synthesizes a pre-market quote from aftermarket data, standard quotes, and history fallback.
- `get_reference_quote(ticker, force_refresh=False, session="close", history=None, target_date=None)` — fetches regular session closing quote or pre-market reference quote with verified 1D price and percentage change vs prior trading day's close, preventing after-hours drift from corrupting daily performance metrics in evening synthesis pipelines.
- `is_market_open()`, `is_premarket()`, `is_trading_day(target_date)`, `get_market_holidays()` — session checks delegated directly to `trading.market_calendar` (see below).
- `screen_stocks(...)` — provider screening with an in-memory screener cache keyed on the sorted parameter set.
- Provider passthroughs: `get_key_metrics`, `get_earnings_history`, `get_analyst_estimates`, `get_financial_growth`, `get_company_profile`.
- Technical indicator computation: `get_technical_indicators` (`apps/engine/tools/technicals.py`) computes RSI-14, MACD, 20D VWAP, SMA-20/50, RVOL, and 52-week range % with optional point-in-time `cutoff_date`.

The manager exposes `client`, `cache_ttl_seconds`, and `provider` as properties with setters, so overrides propagate into the underlying `MarketDataCache`. `_validate_date_coverage` remains as a backward-compatibility alias for `market_transforms.validate_date_coverage`.

#### Session checks (direct calendar delegation)

There is no session adapter module: `MarketDataManager` calls the process-wide `MarketCalendar` (`get_market_calendar()`, see [[entities/market-calendar]]) itself, so the facade and the live trader can never disagree about whether the market is open.

- `is_market_open()` — `await asyncio.to_thread(get_market_calendar().is_open)`. Holiday-, half-day- and ad-hoc-closure-aware when a trading client is wired; weekday + 09:30–16:00 ET plus the offline holiday rules otherwise. A client whose clock cannot be read reports **closed**, so a network blip skips a session instead of trading into a holiday.
- `is_trading_day(target_date=None)` — normalizes `None` (today ET), an ISO string (`target_date[:10]`), a `datetime`, or a `date`, then `await asyncio.to_thread(get_market_calendar().is_session_day, date_obj)`.
- `get_market_holidays()` — derives non-session weekdays for the next 30 days by gathering `calendar.session_for(day)` on worker threads and keeping weekdays whose session is `None`, returning `{"date", "exchange": "NYSE", "isClosed": True}` dicts. No FMP fetch.
- `is_premarket()` — calls the synchronous `trading.market_calendar.is_premarket()` (Mon–Fri 04:00–09:30 ET) directly.
- `_is_known_us_market_holiday_fallback(date_obj)` — delegates to `trading.market_calendar.is_known_us_market_holiday`, which includes Good Friday (computus).

The facade keeps empty `_market_status_cache` / `_holidays_cache` class attributes for attribute compatibility only; the calendar owns the caching.

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
- [[entities/market-calendar]] — the authoritative session calendar this facade delegates to
- [[concepts/execution]]
- [[concepts/vertical-slice-islands]]
- [[concepts/ingestion]]
- [[concepts/multi-horizon-reference]]
