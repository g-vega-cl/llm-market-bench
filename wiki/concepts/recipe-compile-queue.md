---
tags: [recipes, compile, queue, worker, stale-jobs, builder, ux, single-flight, sanitization]
category: concept
---

# Recipe Compile Queue

The Recipe Builder turns a user's natural-language idea into a runnable trading recipe by enqueuing a **compile** job into the `recipe_execution_queue` table and polling for its result. The queue is shared with backtest and live-turn jobs, but compiles run in their own bounded lane so an interactive builder session never queues behind a batch of backtests. This page covers the compile lane's lifecycle, its per-user caps (single-flight + burst window + daily meter), the server-side payload lock that keeps a tampered row from proxying arbitrary LLM calls, and the two-sided recovery for jobs no worker ever claims — a server-side stale sweep and a client-side give-up path.

## Queue Modes and Lanes

`recipe_execution_queue` rows carry a `mode` of `backtest`, `live_turn`, or `compile` (`SUPPORTED_JOB_MODES` in `apps/engine/recipes/worker.py`). The daemon in `apps/engine/recipes/runner.py` drains each lane with its own concurrency:

- **Compile lane** — `_compile_lane_loop`, bounded by `COMPILE_CONCURRENCY` (`RECIPE_COMPILE_CONCURRENCY`, default 3). A compile is interactive: the user is staring at the builder while it runs, so it gets a dedicated semaphore rather than queueing behind backtests.
- **Backtest lane** — clamped to `min(3, max(1, RECIPE_BACKTEST_CONCURRENCY))`.
- **Live-turn lane** — `LIVE_TURN_CONCURRENCY` (`RECIPE_LIVE_CONCURRENCY`, default 10).

## Per-User Caps

Three independent limits guard the compile lane, all enforced in `apps/web/src/features/recipes/builder/compile-queue.ts`:

- **`MAX_PENDING_COMPILES = 1`** — a **single-flight** concurrency lock. A user may have at most one `pending`/`processing` compile at a time; `pendingCompilesMessage()` reads *"You already have a compile in flight. Wait for it to finish, then try again."* (the message is generated from the constant, so raising the cap restores the plural copy automatically).
- **`BUILDER_BURST_LIMIT = 5` per `BUILDER_BURST_WINDOW_MINUTES = 5`** — a short-term burst window. `enqueueCompile` counts the caller's `mode='compile'` rows created since `now − 5 minutes` and refuses with `builderBurstLimitMessage()` (*"Too many build requests (5 in 5 minutes). Wait a few minutes and try again."*) once the count reaches the limit. This bounds a rapid-fire loop that would otherwise stay under the daily meter while still spending provider tokens.
- **`BUILDER_DAILY_LIMIT = 25`** — the daily compile budget, spent by the worker (see [[concepts/recipe-builder-usage]]).

A pending row counts against the single-flight cap until it reaches a terminal status, so a row that never leaves `pending` would hold a user's quota hostage indefinitely — which is exactly what the stale sweep and the client give-up path exist to prevent.

### Atomic Single-Flight Lock (Database)

The application-level in-flight check is a read-then-insert, so two concurrent requests could both observe zero pending rows. Migration `20261123000000_builder_single_flight_lock.sql` closes that race at the storage layer:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_recipe_one_pending_compile_per_user
    ON public.recipe_execution_queue (user_id)
    WHERE mode = 'compile' AND status IN ('pending', 'processing');
```

A second concurrent insert therefore fails with SQLSTATE `23505`, which `enqueueCompile` maps back to `pendingCompilesMessage()` instead of surfacing a raw database error. The index is partial, so it never constrains backtest or live-turn rows, and it releases automatically the moment the row reaches `completed`, `failed`, or `cancelled`.

## Server-Locked Compile Payload

A queue row is data, not a trusted request. Both ends of the lane re-derive the model contract rather than trusting what was stored:

- **Enqueue side (`buildCompilePayload`)** — emits `{ model: 'auto-go', temperature: 0.2, max_tokens: COMPILE_MAX_TOKENS (1200), response_format: { type: 'json_object' }, messages: buildConversation(...) }`. Model, token budget, and JSON mode are server-owned constants.
- **Worker side (`_sanitize_compile_payload`)** — before the meter and before any provider call, the daemon validates and rewrites the stored payload:
  - `messages` must be a non-empty list of at most `COMPILE_MAX_MESSAGES` (9 = 1 system + up to 8 conversation turns);
  - the first message must be `system` or `user`, every later message must be `user` or `assistant` (an injected second `system` turn fails the job);
  - every `content` must be non-empty text, truncated to 8000 chars for `system` and 2200 chars otherwise;
  - the last message must be a `user` turn;
  - `max_tokens` is clamped to `1..COMPILE_MAX_TOKENS` (1200) and defaults to 1200 for a non-int or bool; `temperature` is clamped to `0.0..0.5` and defaults to 0.2;
  - `model` is forced to `auto-go` and `response_format` to `{ "type": "json_object" }`.

A payload that fails validation raises before `consume_builder_compile`, so a tampered row costs no meter and no provider tokens. See [[concepts/recipe-builder-compiler]] for the conversation-level validation (`validateBuilderMessages`) that runs on the way in.

## Server-Side Stale Compile Sweep

The pop RPC only recovers `processing` rows whose heartbeat lapsed. A row that never moved off `pending` has no heartbeat, so without intervention it would sit forever. `fail_stale_compile_jobs(sb, *, timeout_seconds=STALE_COMPILE_SECONDS)` in `apps/engine/recipes/worker.py` closes that gap:

- `STALE_COMPILE_SECONDS = 600` (10 minutes) — matches the existing recovery rule for stalled `processing` rows.
- `STALE_COMPILE_MESSAGE = "The worker never picked this compile up. Try again."`
- It updates rows where `mode = 'compile'`, `status = 'pending'`, and `created_at < now - timeout` to `status = 'failed'`, stamping `error_message` and `completed_at`, returning the number of rows swept.

The compile lane loop (`_compile_lane_loop`) runs this sweep at most once per `STALE_COMPILE_SWEEP_INTERVAL_SECONDS = 60`, tracked via `last_sweep_utc`. A sweep failure is logged with `logger.exception("Stale compile sweep failed")` and does not stop the lane. When rows are swept, the daemon logs `Failed N stale compile job(s) no worker claimed`.

A 60s sweep cannot beat a 5s pop poll, so the sweep alone is not enough: a daemon returning to a 12-minute-old row claims and runs it first. `_execute_compile_job` therefore re-reads `created_at` and raises `STALE_COMPILE_MESSAGE` **before** the meter and before any provider call. A late job fails instead of charging a user for a compile they stopped waiting for. Proven live: a synthetic 12-minute-old row was claimed and completed before this guard, and fails without a provider call after it.

Two more live findings from the same probe round: a provider timeout recorded `error_message = ""` (the row was `failed` with no text, so the UI could only say "failed"), and 45s was too tight — a real compile hit 46s against the free provider. `_failure_text()` now returns "The model took too long to answer. Try again." for `httpx.TimeoutException` and `<Type>: the job stopped without a message.` otherwise, and the budget is `COMPILE_TIMEOUT_SECONDS` = 60s (`RECIPE_COMPILE_TIMEOUT_SECONDS`, floor 30).

## Client-Side Give-Up Path

The builder UI (`apps/web/src/features/recipes/builder/use-builder-chat.ts`) does not count up forever on an unclaimed job. Two thresholds in `compile-queue.ts` drive the behavior:

- `QUEUE_SLOW_MS = 60_000` — after a minute, `queuedHint(elapsedMs)` returns an honest strip line: *"still queued — the worker is busy. This is cancelled automatically after 5 minutes, and a stuck job is cleared from your quota after 10."* Before that it returns `null`.
- `QUEUE_ABANDON_MS = 300_000` — `isQueueAbandoned(elapsedMs)` flips true at five minutes.

The hook exposes `statusDetail` (the `queuedHint` value while a job is in flight) which `BuilderChatPanel` forwards to `BuilderStatusStrip` as `detail`. An `elapsedRef` mirrors `elapsedMs` so the poll interval can read the current elapsed time without render state.

When `isQueueAbandoned` fires, the abandon effect:

1. clears the in-flight latch and `jobId`,
2. calls `fail(ABANDONED_MESSAGE, 'abandoned')` — *"The builder never picked this request up, so it was cancelled. Try again — nothing was spent on it."*, emitted as `builder_failed` with `reason_code: 'abandoned'`,
3. fires `cancelCompileFn({ data: { jobId } })` best-effort (a failure is swallowed; the daemon sweep is the backstop for a closed tab).

The poll `refetchInterval` also stops returning `2000` once the client has given up, so it stops hammering the server while the abandon effect cancels the row.

## Failure Taxonomy

Every failure path in `useBuilderChat` funnels through `fail(message, code)`, which emits `builder_failed` with a short, bounded `reason_code` (`BuilderFailureCode`) plus the human `reason` (truncated to 120 chars). The code is the analytics breakdown dimension; the message is kept only for debugging, because a 120-char sentence as a breakdown value produces one row per distinct sentence. The codes:

- `no_reply` — the poll returned no usable content, or the transport resolved to `undefined` (envelope-less reply)
- `job_failed` — the queued job reached `failed`/`cancelled` (its `error_message` becomes the `reason`)
- `enqueue_rejected` — `enqueueCompileFn` threw (meter refusal, single-flight cap, burst window, auth, transport)
- `abandoned` — the client gave up on an unclaimed job at `QUEUE_ABANDON_MS`

## Cancelling a Compile

`cancelCompile(jobId, userId)` in `compile-queue.ts` updates `recipe_execution_queue` to `status = 'cancelled'` with `cancelled_at`, scoped to `id`, `user_id`, `mode = 'compile'`, and `status = 'pending'`. Only a still-pending row is touched, so a worker that already claimed the job keeps its result — the cancel just frees the single-flight slot. A database error is re-thrown as `` `${error.code}: ${error.message}` `` rather than silently swallowed.

`cancelCompileFn` is the `createServerFn` wrapper: it authenticates via `getAuthServerClient`, rejects unauthenticated callers (`Unauthorized: sign in to build a recipe`), and calls `cancelCompile` with the authenticated user's id. Its validator runs `validateJobId` (non-empty string, at most `MAX_JOB_ID_CHARS` = 128) so a malformed id never reaches the query.

## Polling and Result Handling

`fetchCompileJobFn` reads `id, status, progress_pct, result_json, error_message` for a job. The hook polls every 2 seconds while the status is `pending` or `processing` (`isInFlight`), and stops on any terminal status.

`readCompileJob(jobId, userId)` validates the job id, scopes the read to the caller and `mode = 'compile'`, and — for a `completed` row whose `result_json.content` is a string — runs `sanitizeCompileResult()` and re-serializes the sanitized reply back into `result_json.content`. Raw model prose therefore never reaches the browser: an off-schema answer degrades to the `fallback: true` starter recipe before the client parses it. A completed job's `result_json` is then parsed into a recipe; an unusable reply falls back to the closest working template.

## Related

- [[entities/recipe-studio]] — the Recipe Builder UI surface
- [[entities/recipe-playground]] — running compiled recipes
- [[entities/recipe-live-status]] — live-turn status surface
- [[concepts/recipe-builder-compiler]] — how an idea becomes a recipe, including conversation validation and result sanitization
- [[concepts/recipe-builder-usage]] — builder usage flow and the daily meter
- [[concepts/recipe-ops-telemetry]] — queue and worker telemetry
- [[entities/database]] — `recipe_execution_queue` table inventory and the single-flight index
