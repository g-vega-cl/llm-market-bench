---
tags: [engine, market-hours, calendar, alpaca, trading, session]
category: entity
---

# Market Calendar

`apps/engine/trading/market_calendar.py` is the authoritative US equity session calendar. `MarketCalendar.is_open()` answers "is the regular session running right now"; `MarketCalendar.session_for(day)` answers "is `day` a session day, and when does it open and close". Every clock gate in the engine reads from it — the live trader daemon's session gate, `MarketDataManager` (see [[entities/market-data]]), the recipe runner, the systematic-strategy hooks window, and the 30-minute audit harness.

It exists because weekday + 09:30–16:00 ET arithmetic does not know about market holidays, half-day early closes, or ad-hoc closures, and reported the market as open on Thanksgiving.

## Policy (decided deliberately)

| Situation | Behavior |
| :--- | :--- |
| No trading client (local dev, unit tests, audit harness) | Weekday/regular-hours arithmetic plus the offline holiday rules |
| Client wired, `/v2/clock` readable | Alpaca's answer is authoritative |
| Client wired, clock call fails | **Closed** — a network blip skips a session instead of trading into a holiday |
| Client wired, `/v2/calendar` fails | `session_for` returns `None` (closed) and caches the failure for the TTL |

The clock answer is cached for `ttl_seconds` (default `60`) because the daemon's tape poller consults the gate every 10 seconds. A cached clock can never outlive its own close: when Alpaca reports `is_open`, `next_close` from the same payload is compared against the requested instant, so a clock read at `15:59:30` is not served as open at `16:00:20` (Alpaca queues orders submitted while closed, so trusting the payload beats shrinking the TTL).

## `MarketCalendar`

`MarketCalendar(client=None, ttl_seconds=60.0, call_timeout_seconds=5.0)`

| Member | Contract |
| :--- | :--- |
| `client` / `has_client` | The injected paper `TradingClient`, if any. `None` means the offline path. |
| `is_open(now_dt=None) -> bool` | Whether the regular session is running now. Offline: weekday, non-holiday, `09:30 <= t < 16:00` ET. Wired: `clock.is_open` **and** `now < clock.next_close`. Unreadable clock → `False`. |
| `seconds_to_next_open(now_dt=None) -> float` | Seconds until the next regular open. Wired: from `clock.next_open`. Offline: next `09:30 ET` on a session day within a 10-day scan, else `86400.0`. |
| `session_for(day) -> (open_at, close_at) \| None` | Regular session bounds in ET for `day`, or `None` when the market is shut. Wired: Alpaca `/v2/calendar`, which omits holidays and reports the early close on half days. Offline: `(09:30, 16:00)` ET on a session day. Cached per day. |
| `is_session_day(day) -> bool` | `session_for(day) is not None`. |

`_as_et()` treats a naive `datetime` as US Eastern and leaves aware values untouched, so cache arithmetic never raises on a naive input.

### Module-level gate

| Symbol | Purpose |
| :--- | :--- |
| `_default_calendar` | The process-wide `MarketCalendar` instance |
| `configure_market_calendar(client=None, ttl_seconds=60)` | Install the calendar used by the module-level gate; called once at daemon start (`apps/engine/trading/runner.py`, `apps/engine/scripts/audit_30min_trader.py`) with `broker.client` |
| `get_market_calendar()` | Read the current instance |
| `is_market_session_active(now_dt=None)` | Shorthand for `_default_calendar.is_open(now_dt)` |
| `seconds_to_next_open(now_dt=None)` | Shorthand for `_default_calendar.seconds_to_next_open(now_dt)` |
| `is_premarket(now_dt=None)` | Whether it is 04:00–09:30 ET on a weekday. Pure clock arithmetic (no calendar lookup, no client): `now_dt` is normalized through `_as_et` and converted to ET, weekends return `False`, and the window is `[04:00, 09:30)` ET. Consumed by `MarketDataManager.is_premarket()` (see [[entities/market-data]]). |

Because the instance is a module-level singleton, `apps/engine/conftest.py` installs an autouse `_reset_market_calendar` fixture that calls `configure_market_calendar(None)` after every test — a test that ran the daemon would otherwise leak its (possibly mocked) client into every test that follows.

## Offline Holiday Rules

`is_known_us_market_holiday(day)` is the fallback used only when no client is wired. It covers New Year's Day (Jan 1, observed Jan 2 when Jan 1 falls on a Sunday), Martin Luther King Jr. Day, Washington's Birthday, **Good Friday**, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving, and Christmas, each with its observed-date shift. It deliberately does **not** close December 31 when January 1 falls on a Saturday: under NYSE Rule 7.2 the exchange keeps that session open for year-end accounting (2010 and 2021 both traded). Good Friday is computed from the anonymous Gregorian Easter algorithm (`_good_friday(year)` = Western Easter − 2 days), so the offline path and the exchange calendar agree about the one holiday that is not a fixed-date or nth-weekday rule.

`_local_is_open`, `_local_is_session_day`, and `_local_seconds_to_next_open` combine those rules with `REGULAR_OPEN_MINUTES = 570` (09:30 ET). `_local_close_time(day)` supplies the close: **13:00 ET** on the scheduled half days (the day after Thanksgiving, July 3, December 24) and 16:00 otherwise, so a keyless lane no longer trades three hours past a half-day bell.

Every consumer delegates here: the live trader (`is_market_session_active`), the hooks window, the marks refresh, the recipe lane, `MarketDataManager`, and the 30-minute audit harness. The recipe runner's private Good Friday/09:30-16:00 arithmetic was deleted in favour of this module. `due_trading_slot` now stops at the real close: on a 13:00 half day the 13:00 slot still fires at the bell (the same 20-minute window the 16:00 slot has always had), but 13:30 onward is never scheduled, so six recipe turns and their mirrored limit orders no longer run after the close. The recipe daemon does not call `configure_market_calendar`, so it sees these offline rules rather than the exchange calendar and cannot know an ad-hoc closure.

## Threading and Timeouts

`alpaca-py`'s requests transport sets no timeout, and the gate is consulted from a 10-second loop on the daemon's single event loop — one hung TLS connection would freeze the tape broadcast, the agent turn, and the QA worker. Every SDK call therefore runs on a single-worker `ThreadPoolExecutor` (`_call(fn)` → `_call_bounded`, hard bound default `5.0`s).

A timed-out call cannot be cancelled (the thread is inside `requests`), so on timeout the pool is **discarded and rebuilt**: the hung thread is abandoned, later callers get a fresh worker, and the failure costs one thread per hang instead of a permanently dead gate. `apps/engine/trading/runner.py` also calls the gate through `asyncio.to_thread` at all four call sites, so even the bounded call never blocks the event loop.

Session lookups cache failures too (`_session_error_at`, TTL-scoped): an Alpaca outage would otherwise turn every 5-minute hook tick into another blocking request.

## Consumers

- `apps/engine/trading/runner.py` — `is_market_session_active()`, `calculate_seconds_to_market_open()`, and `_is_hooks_window()` (regular session plus the 5-minute closing-print tail via `session_for`). See [[entities/live-agent-trader]] and [[concepts/systematic-strategy-hooks]].
- `apps/engine/execution/market_data.py` — `MarketDataManager` calls `get_market_calendar()` directly for `is_market_open()`, `is_trading_day()`, and `get_market_holidays()`, and the synchronous `is_premarket()` for pre-market detection (see [[entities/market-data]]).
- `apps/engine/recipes/runner.py` — `_is_trading_day_et` calls `get_market_calendar().is_session_day` on a worker thread, after its own weekend/holiday fallback check.
- `apps/engine/scripts/audit_30min_trader.py` — wires the calendar from `AlpacaBroker.client` before the audit run.

## Related

- [[entities/live-agent-trader]] — the daemon whose session gate and hooks window delegate here
- [[entities/market-data]] — `MarketDataManager`, which delegates its session checks here
- [[concepts/systematic-strategy-hooks]] — the hooks window derived from `session_for`
- [[entities/secondary-minipc-edge]] — the host running the trader daemon
- [[concepts/alpaca-order-sync]] — the broker whose clock is authoritative when wired
