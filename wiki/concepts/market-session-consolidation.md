---
tags: [market-calendar, market-session, trading-day, premarket, consolidation, execution]
category: concept
---

# Market Session Consolidation

`trading.market_calendar` (`apps/engine/trading/market_calendar.py`) is the **single implementation** of US equity market-session knowledge. The former `MarketSessionManager` adapter (apps/engine/execution/market_session.py) has been removed entirely — it used to own its own FMP holiday fetch plus hand-rolled rules that duplicated and disagreed with the Alpaca-backed gate the live trader uses. Every consumer now reads the calendar directly.

## Why It Was Consolidated

Two independent session implementations meant two sources of truth for "is the market open / is today a trading day / is it premarket". The Alpaca-backed `MarketCalendar` (`/v2/clock` and `/v2/calendar` when a trading client is wired, the same rule set as the offline fallback otherwise) is now authoritative. The async surface that `execution/market_data.py` and `recipes/runner.py` awaited is preserved by running each bounded calendar lookup on a worker thread via `asyncio.to_thread`, so callers never block their event loop.

## Delegation Points

`MarketDataManager` (`apps/engine/execution/market_data.py`) no longer holds a `self.session` attribute. Its async methods delegate straight to the calendar:

| Method | Implementation |
| :--- | :--- |
| `is_market_open()` | `await asyncio.to_thread(get_market_calendar().is_open)` |
| `get_market_holidays()` | Derives non-session weekdays for the next 30 days from `calendar.session_for(day)`; returns `{"date", "exchange": "NYSE", "isClosed": True}` entries |
| `is_trading_day(target_date)` | Normalizes `None`/`str`/`datetime`/`date` to a date, then `await asyncio.to_thread(get_market_calendar().is_session_day, date_obj)` |
| `is_premarket()` | `calendar_is_premarket()` |
| `_is_known_us_market_holiday_fallback(date_obj)` | `is_known_us_market_holiday(date_obj)` |

The class-level `_market_status_cache` / `_holidays_cache` are now plain dicts on `MarketDataManager`; the `_LockProxy` indirection that proxied the removed manager's locks is gone.

`recipes/runner.py` (`_is_trading_day_et`) also calls `await asyncio.to_thread(get_market_calendar().is_session_day, dt_et.date())`, keeping its weekend/holiday fallback and returning `True` when the calendar lookup raises.

## New `is_premarket` Helper

`trading/market_calendar.py` now exposes a module-level `is_premarket(now_dt=None)`:

- Returns `False` on weekends (`weekday() >= 5`).
- Otherwise `True` when the ET clock is in `[04:00, 09:30)`.
- Accepts an optional `now_dt` (normalized to ET via `_as_et`) for deterministic testing; defaults to `datetime.now(ET)`.

This replaces the static `MarketSessionManager.is_premarket()` that lived in the deleted adapter.

## Offline Fallback

When no trading client is wired, `MarketCalendar` uses the same rule set as the offline fallback — `is_known_us_market_holiday(date_obj)` remains the rule-based, network-free holiday check (New Year's, MLK, Washington's Birthday, Good Friday, Memorial Day, Juneteenth, observed July 4, Labor Day, Thanksgiving, Christmas). Tests that previously patched `execution.market_session.datetime` now patch `trading.market_calendar.datetime`.

## Related

- [[entities/market-calendar]] — the calendar implementation
- [[entities/market-data]] — `MarketDataManager` delegation surface
- [[entities/engine]] — the Python data engine
- [[concepts/execution]] — trading execution layer
