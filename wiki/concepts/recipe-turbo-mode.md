---
tags: [recipes, turbo, scheduler, market-hours, database, live]
category: concept
---

# Recipe Turbo Mode

Turbo is a one-hour, 5-minute-cadence boost for a single live Push v2 recipe. A normal live bot runs once per 30-minute ET market slot (`09:30`–`16:00` ET); a Turbo bot additionally runs every 5 minutes inside its window. Each user gets **one Turbo activation per ET trading day**.

## Activation Contract

- **When** — `Mon–Fri 09:30:00–15:55:00 ET`, excluding US market holidays (Good Friday included). Activation is refused inside the last five minutes of the session so at least one 5-minute tick can still fire.
- **Expiry** — `min(now + 1 hour, today 16:00 ET)`. A Turbo activated at `15:25 ET` therefore expires at `16:00 ET`, not `16:25 ET`.
- **Preconditions** — the caller must own the recipe, the recipe must be `is_live = true`, must not be archived, and the owner must not have consumed the day's allowance.
- **Side effect** — the activation immediately enqueues a `live_turn` job (`priority = 1`, provider `free-llm-proxy`, model `auto-go`) unless the recipe already holds a `pending`/`processing` `live_turn` job, in which case that job id is returned and nothing new is inserted.

## Database State (`supabase/migrations/20261120000000_add_recipe_turbo_mode.sql`)

| Object | Purpose |
| :--- | :--- |
| `strategy_recipes.turbo_expires_at TIMESTAMPTZ` | Active Turbo window for the recipe; `NULL` when inactive. |
| `strategy_recipes_turbo_requires_live` CHECK | Makes an illegal state unrepresentable: `(is_live = TRUE AND archived_at IS NULL) OR turbo_expires_at IS NULL`. A paused or archived recipe can never carry a Turbo window. |
| `idx_strategy_recipes_turbo_active` | Partial index on `turbo_expires_at` `WHERE is_live = TRUE AND archived_at IS NULL AND turbo_expires_at IS NOT NULL` — the daemon's Turbo query path. |
| `idx_recipe_queue_live_turn_created` | Partial index on `recipe_execution_queue (created_at DESC)` `WHERE mode = 'live_turn' AND status <> 'cancelled'`. |
| `idx_recipe_one_open_live_turn_per_recipe` | Unique partial index on `(recipe_id)` `WHERE mode = 'live_turn' AND status IN ('pending','processing')`, so a 5-minute tick and a 30-minute slot can never run two live turns for the same recipe concurrently. The migration first cancels surplus `pending` rows (keeping the `processing` one, else the newest) so the index can be built. |
| `recipe_user_quotas.last_turbo_et_date DATE` | Per-user daily allowance, compared against the ET date derived inside Postgres. |

### `activate_recipe_turbo(p_user_id UUID, p_recipe_id UUID)`

`SECURITY DEFINER`, `SET search_path = public`, `EXECUTE` revoked from `PUBLIC`/`anon`/`authenticated` and granted only to `service_role`. Returns `TABLE (recipe_id UUID, turbo_expires_at TIMESTAMPTZ, enqueued_job_id UUID)`.

The clock lives in the database, never in the caller: `NOW()` is converted with `AT TIME ZONE 'America/New_York'` to derive the ET date/time, and the close is recomputed as `(et_date + 16:00) AT TIME ZONE 'America/New_York'`, so EDT/EST both resolve correctly. The function then, in one transaction:

1. rejects a missing argument, an out-of-hours ET time, or a weekend date;
2. upserts the caller's `recipe_user_quotas` row and locks it `FOR UPDATE`;
3. raises `Daily Turbo limit reached (1/1 used today ET)` when `last_turbo_et_date` already equals today's ET date;
4. locks the `strategy_recipes` row and rejects `Recipe not found`, cross-user ownership, an archived recipe, and a recipe that is not live;
5. stamps `last_turbo_et_date`, writes `turbo_expires_at = LEAST(now + 1h, close)`, and enqueues the first `live_turn` job when none is open.

The 1/day rule is therefore enforced by a locked counter, not by a read-then-write race in the browser.

## Runner Scheduling (`apps/engine/recipes/runner.py`)

```
LIVE_SLOTS_ET           14 half-hour slots, 09:30 .. 16:00 ET
SLOT_WINDOW_SECONDS     1200  (20-minute trigger window per slot)
TURBO_INTERVAL_SECONDS  300   (5-minute Turbo cadence)
TURBO_POLL_INTERVAL_SECONDS 30 (poll active Turbo bots at most every 30s)
NEWS_SYNC_MIN_INTERVAL_SECONDS  300
PUBLIC_STATS_MIN_INTERVAL_SECONDS 60
```

- **`is_us_market_hours_et(now)`** — `Mon–Fri 09:30 <= t <= 16:00 ET`, excluding weekends and the rule-based US holiday fallback. The fallback (`_is_us_holiday_fallback`) combines `MarketSessionManager.is_known_us_market_holiday_fallback` with `_good_friday_date` computed from the Anonymous Gregorian Easter algorithm, so Good Friday is a closed session on both sides of the stack.
- **`due_trading_slot(now, last_slot_key)`** — matches any of the 14 slots inside the 20-minute window, deduplicates via `last_slot_key`, and returns `None` on weekends, holidays, pre-open, and after the `16:00` window.
- **`_is_trading_day_et(now)`** — weekend/holiday fallback first, then FMP-backed `MarketSessionManager().is_trading_day(...)`; a lookup failure logs at debug level and allows the day.
- **`_fetch_active_turbo_recipes(sb)`** — pages every `is_live = true`, `archived_at IS NULL`, `turbo_expires_at > now` recipe.
- **`enqueue_turbo_recipes(sb, now_utc=...)`** — returns `0` outside market hours; otherwise skips recipes that already hold a job since `now - 5 minutes`, skips invalid single-stage graphs, and inserts `live_turn` jobs through `_insert_live_jobs_idempotent`.
- **`run_live_lane_tick(sb, now_utc, state)`** — the single per-tick decision function over a `LiveLaneState` dataclass (`last_slot_key`, `last_news_sync_utc`, `last_turbo_poll_utc`, `last_stats_refresh_utc`). Priority order: (1) a due 30-minute slot runs `run_scheduled_slot`; (2) otherwise, during market hours and at most once per 30s, `enqueue_turbo_recipes`, with a news sync only when at least one Turbo job was enqueued *and* `NEWS_SYNC_MIN_INTERVAL_SECONDS` elapsed; (3) always drain the `live_turn` lane, refreshing public stats at most once per `PUBLIC_STATS_MIN_INTERVAL_SECONDS` when something ran. `_live_lane_loop` is a thin `while True` around it at `POLL_INTERVAL_SECONDS = 5`.
- **Slot retry** — a failed `run_scheduled_slot` logs and returns **without** advancing `last_slot_key`, so the next tick retries the same slot instead of silently skipping it.

### Double-fire suppression and replica-lag tolerance

- `enqueue_live_recipes_with_stats(..., recent_turbo_cutoff_utc=...)` skips a recipe that already ran a Turbo turn in the 5 minutes before the 30-minute slot. Those skips are counted as `skipped_recent_turbo` rather than `skipped_open`, so a Turbo bot cannot inflate the high-skip-ratio ops alarm.
- The `run_scheduled_slot` passes `slot_start_utc` (canonical slot start) and `recent_turbo_cutoff_utc = now - 300s` separately; the recent-Turbo lookup is only performed when that cutoff is earlier than the slot start.
- `_insert_live_jobs_idempotent(sb, new_jobs)` attempts the batch insert and, on a `23505` / `duplicate key` error (possible when the read replica's open-job view lags the unique index), retries row by row, keeping the successful inserts and logging the duplicates at debug level.

## Web Surface (`apps/web/src/features/recipes/utils/market-hours.ts`)

A single pure module shared by the studio, the live status page, and the quota API:

| Helper | Contract |
| :--- | :--- |
| `getEtClockParts(now)` | `{ etDate, weekday, hour, minute, totalMinutes, isoOffset }` from `Intl.DateTimeFormat` with `timeZone: 'America/New_York'` and `timeZoneName: 'shortOffset'`. |
| `getEtDateString(now)` | `YYYY-MM-DD` ET date, used for `turboUsedToday`. |
| `isKnownUsMarketHolidayEt(etDate)` | Rule-based holiday set matching the engine fallback: New Year's, MLK, Presidents', Memorial, Juneteenth, Independence, Labor, Thanksgiving, Christmas (observed-date handling), plus Good Friday from the Easter algorithm. |
| `isRegularMarketHoursEt(now)` | Weekday, non-holiday, `>= 09:30` and `< 16:00` ET. |
| `canActivateTurboEt(now)` | Same gates but `< 15:55` ET (five minutes of runway before the close). |
| `computeTurboExpiryIso(now)` | `min(now + 1h, today 16:00 ET)` as a UTC ISO string. |
| `isTurboActive(expiresAt, now)` | Un-expired window **and** regular market hours. |
| `formatTurboRemainingLabel(expiresAt, now)` | `` `<N>m left` `` when active, otherwise `null`. |
| `getNextLiveSlotLabel(now)` | `HH:MM ET today`, `09:30 ET tomorrow`, `09:30 ET Monday`, or `09:30 ET next trading day`. |

Two user-facing cadence labels are exported from the same module so no surface hardcodes the copy: `LIVE_CADENCE_LABEL = '30m'` and `TURBO_CADENCE_LABEL = '5m'`. They are the single spelling used by the compiled-bot workspace's live badge (`LIVE ON (30m)`) and its Turbo next-run line (`Next run within 5m (Turbo) · <n>m left`), keeping the copy aligned with the schedule it describes. See [[entities/recipe-studio]].

`TurboButton.tsx` renders one of four mutually exclusive states, re-reading the clock every 15s unless an external `now` is supplied: active countdown (`Turbo: 42m left (5m)`, solid accent, disabled), exhausted allowance (`Turbo Used Today`), market closed (`Turbo (Market Closed)`), or the actionable `Turbo (5m x 1h)` button. Every clock-derived label carries `suppressHydrationWarning` so SSR/hydration skew cannot warn.

`activateRecipeTurbo(recipeId, userId, now)` in `api/recipes-quota-api.ts` gates locally with `canActivateTurboEt(now)` and then calls the 2-argument RPC, returning `{ recipeId, turboExpiresAt, enqueuedJobId }`. It is exposed to the browser as `activateRecipeTurboFn` (auth-gated `createServerFn`). The studio (`StudioActionBar` → `TurboButton`) and the live status page both call it, update `turbo_expires_at` on the local recipe summary, set `turboUsedToday`, and refresh quota state.

## Pausing and Archiving Clear Turbo

Turbo can never outlive the live schedule:

- `toggleLiveSchedule(recipeId, false, userId)` writes `is_live: false` **and** `turbo_expires_at: null`, then cancels that recipe's `pending` `live_turn` queue rows (`status = 'cancelled'`, `cancelled_at`). A cancel failure is logged and never rolled back.
- `archiveRecipe` writes `archived_at`, `is_live: false`, and `turbo_expires_at: null` in the same update.
- The `strategy_recipes_turbo_requires_live` CHECK is the backstop if either path is bypassed.

## Live Lane Throttle Windows

| Throttle | Window | Purpose |
| :--- | :--- | :--- |
| `TURBO_POLL_INTERVAL_SECONDS` | 30s | Prevent re-polling active Turbo bots on every 5s tick. |
| `NEWS_SYNC_MIN_INTERVAL_SECONDS` | 300s | Only sync live news into the corpus when a Turbo enqueue actually happened. |
| `PUBLIC_STATS_MIN_INTERVAL_SECONDS` | 60s | Only refresh the public board when the live lane drained work. |

## Tests

- `apps/engine/recipes/test_runner.py` — 14-slot `LIVE_SLOTS_ET` shape, slot matching/dedup across `10:00`/`11:00`/`15:30`/`16:00`, rejection of pre-open, post-close, weekends, Thanksgiving and Good Friday, `is_us_market_hours_et` boundaries, `enqueue_turbo_recipes` (inserts only un-expired, non-recent bots, does nothing after hours), `run_live_lane_tick` throttles (no re-poll at +10s, re-poll at +31s, no news/stats inside their windows), slot-retry without advancing `last_slot_key`, `run_scheduled_slot` passing distinct slot/recent-turbo cutoffs, no ops event when the only skip is a recent Turbo, and the row-by-row `23505` fallback.
- `apps/web/src/features/recipes/utils/market-hours.test.ts` — market-hours/holiday/Good Friday detection, the `15:54` vs `15:55` activation cutoff, expiry capping at `16:00 ET` in both EST and EDT, active/remaining-label arithmetic, and next-slot labels.
- `apps/web/src/features/recipes/api/recipes-quota-api.test.ts` — Turbo RPC arg shape, rejection outside market hours without an RPC call, and `turbo_expires_at: null` + pending-job cancellation when pausing.
- `apps/web/src/features/recipes/pages/RecipeOverviewPage.test.tsx` and `RecipeStudioPage.runs.test.tsx` — Turbo activation from both surfaces and the resulting countdown button (Turbo moved to the Overview card when the Live hub was retired; its `useBotHeaderActions` state owns the countdown).

## Related

- [[entities/recipe-studio]] — the studio, its runner daemon, and the live-turn lane this mode rides on
- [[entities/recipe-live-status]] — the live page that hosts the Turbo control and countdown
- [[entities/database]] — `strategy_recipes`, `recipe_user_quotas`, `recipe_execution_queue`, and the `activate_recipe_turbo` RPC
- [[concepts/recipe-ops-telemetry]] — enqueue counters, including `skipped_recent_turbo`
- [[concepts/recipe-backtest-concurrency]] — the sibling lane guard for backtests
- [[concepts/state-machines]] — where queue and recipe lifecycles are registered
- [[concepts/zero-lookahead-materialization]] — why every run is executed point-in-time
