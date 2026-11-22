---
tags: [recipes, compile, queue, worker, stale-jobs, builder, ux]
category: concept
---

# Recipe Compile Queue

The Recipe Builder turns a user's natural-language idea into a runnable trading recipe by enqueuing a **compile** job into the `recipe_execution_queue` table and polling for its result. The queue is shared with backtest and live-turn jobs, but compiles run in their own bounded lane so an interactive builder session never queues behind a batch of backtests. This page covers the compile lane's lifecycle, its per-user caps, and the two-sided recovery for jobs no worker ever claims — a server-side stale sweep and a client-side give-up path.

## Queue Modes and Lanes

`recipe_execution_queue` rows carry a `mode` of `backtest`, `live_turn`, or `compile` (`SUPPORTED_JOB_MODES` in `apps/engine/recipes/worker.py`). The daemon in `apps/engine/recipes/runner.py` drains each lane with its own concurrency:

- **Compile lane** — `_compile_lane_loop`, bounded by `COMPILE_CONCURRENCY` (`RECIPE_COMPILE_CONCURRENCY`, default 3). A compile is interactive: the user is staring at the builder while it runs, so it gets a dedicated semaphore rather than queueing behind backtests.
- **Backtest lane** — clamped to `min(3, max(1, RECIPE_BACKTEST_CONCURRENCY))`.
- **Live-turn lane** — `LIVE_TURN_CONCURRENCY` (`RECIPE_LIVE_CONCURRENCY`, default 10).

## Per-User Caps

- `MAX_PENDING_COMPILES = 2` — in-flight cap. With the meter spent by the worker, enqueues alone must not fan out.
- `BUILDER_DAILY_LIMIT = 25` — daily compile budget.

Both are enforced in `apps/web/src/features/recipes/builder/compile-queue.ts`. A pending row counts against the cap until it reaches a terminal status, so a row that never leaves `pending` would hold a user's quota hostage indefinitely — which is exactly what the stale sweep and the client give-up path exist to prevent.

## Server-Side Stale Compile Sweep

The pop RPC only recovers `processing` rows whose heartbeat lapsed. A row that never moved off `pending` has no heartbeat, so without intervention it would sit forever. `fail_stale_compile_jobs(sb, *, timeout_seconds=STALE_COMPILE_SECONDS)` in `apps/engine/recipes/worker.py` closes that gap:

- `STALE_COMPILE_SECONDS = 600` (10 minutes) — matches the existing recovery rule for stalled `processing` rows.
- `STALE_COMPILE_MESSAGE = "The worker never picked this compile up. Try again."`
- It updates rows where `mode = 'compile'`, `status = 'pending'`, and `created_at < now - timeout` to `status = 'failed'`, stamping `error_message` and `completed_at`, returning the number of rows swept.

The compile lane loop (`_compile_lane_loop`) runs this sweep at most once per `STALE_COMPILE_SWEEP_INTERVAL_SECONDS = 60`, tracked via `last_sweep_utc`. A sweep failure is logged with `logger.exception("Stale compile sweep failed")` and does not stop the lane. When rows are swept, the daemon logs `Failed N stale compile job(s) no worker claimed`.

A 60s sweep cannot beat a 5s pop poll, so the sweep alone is not enough: a daemon returning to a 12-minute-old row claims and runs it first. `_execute_compile_job` therefore re-reads `created_at` and raises `STALE_COMPILE_MESSAGE` **before** the meter and before any provider call. A late job fails instead of charging a user for a compile they stopped waiting for. Proven live: a synthetic 12-minute-old row was claimed and completed before this guard, and fails without a provider call after it.

## Client-Side Give-Up Path

The builder UI (`apps/web/src/features/recipes/builder/use-builder-chat.ts`) does not count up forever on an unclaimed job. Two thresholds in `compile-queue.ts` drive the behavior:

- `QUEUE_SLOW_MS = 60_000` — after a minute, `queuedHint(elapsedMs)` returns an honest strip line: *"still queued — the worker is busy. This is cancelled automatically after 5 minutes, and a stuck job is cleared from your quota after 10."* Before that it returns `null`.
- `QUEUE_ABANDON_MS = 300_000` — `isQueueAbandoned(elapsedMs)` flips true at five minutes.

The hook exposes `statusDetail` (the `queuedHint` value while a job is in flight) which `BuilderChatPanel` forwards to `BuilderStatusStrip` as `detail`. An `elapsedRef` mirrors `elapsedMs` so the poll interval can read the current elapsed time without render state.

When `isQueueAbandoned` fires, the abandon effect:

1. clears the in-flight latch and `jobId`,
2. calls `fail(ABANDONED_MESSAGE)` — *"The builder never picked this request up, so it was cancelled. Try again — nothing was spent on it."*,
3. fires `cancelCompileFn({ data: { jobId } })` best-effort (a failure is swallowed; the daemon sweep is the backstop for a closed tab).

The poll `refetchInterval` also stops returning `2000` once the client has given up, so it stops hammering the server while the abandon effect cancels the row.

## Cancelling a Compile

`cancelCompile(jobId, userId)` in `compile-queue.ts` updates `recipe_execution_queue` to `status = 'cancelled'` with `cancelled_at`, scoped to `id`, `user_id`, `mode = 'compile'`, and `status = 'pending'`. Only a still-pending row is touched, so a worker that already claimed the job keeps its result — the cancel just frees the per-user cap. A database error is re-thrown as `` `${error.code}: ${error.message}` `` rather than silently swallowed.

`cancelCompileFn` is the `createServerFn` wrapper: it authenticates via `getAuthServerClient`, rejects unauthenticated callers (`Unauthorized: sign in to build a recipe`), and calls `cancelCompile` with the authenticated user's id.

## Polling and Result Handling

`fetchCompileJobFn` reads `id, status, progress_pct, result_json, error_message` for a job. The hook polls every 2 seconds while the status is `pending` or `processing` (`isInFlight`), and stops on any terminal status. A completed job's `result_json` is parsed into a recipe; an unusable reply falls back to the closest working template.

## Related

- [[entities/recipe-studio]] — the Recipe Builder UI surface
- [[entities/recipe-playground]] — running compiled recipes
- [[entities/recipe-live-status]] — live-turn status surface
- [[concepts/recipe-builder-compiler]] — how an idea becomes a recipe
- [[concepts/recipe-builder-usage]] — builder usage flow
- [[concepts/recipe-ops-telemetry]] — queue and worker telemetry
- [[entities/database]] — `recipe_execution_queue` table inventory
