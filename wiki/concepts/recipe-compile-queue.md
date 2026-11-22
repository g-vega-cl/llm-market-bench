---
tags: [recipe, builder, compile, queue, async, supabase, worker, auto-go, tanstack-query]
category: concept
---

# Recipe Compile Queue

The Recipe Builder's `/build` chat no longer compiles a strategy inside a synchronous server-function call. Instead, `send` enqueues a **compile job** onto the shared `recipe_execution_queue` table, and the hook polls the job until a worker settles it. The web tier owns prompt construction and recipe validation; the daemon owns the actual model call. This decouples the visitor's request from the origin's hard timeout and lets several users wait on the model at once.

## Why It Exists

The origin severs a synchronous server-function call somewhere between a 27.8s success and a 30.1s Cloudflare 502 (measured on production), and the 502 body is JSON with no reply envelope — which the Start client silently unwraps to `undefined`. A single auto-go chat completion can easily exceed that ceiling, so the old in-request compile either timed out or returned an envelope-less payload that crashed the transcript. Moving the model call onto the queue means the HTTP request only has to enqueue and poll; the long-running work happens in the worker where no origin timeout applies.

## Queue Schema (`supabase/migrations/20261122150000_recipe_compile_queue.sql`)

Compiles reuse the existing `public.recipe_execution_queue` table rather than a dedicated one:

- `recipe_id` is now **nullable** — a compile has no owning recipe; it carries its own conversation payload.
- `payload_json JSONB` holds the **prepared auto-go request body**, built server-side by the web app so the model contract stays in one language (TypeScript). It is `null` for recipe jobs.
- The `mode` check constraint is dropped and recreated to admit `'compile'` alongside `'preview'`, `'backtest'`, and `'live_turn'`.
- The existing pickup index `(mode, priority, created_at) WHERE status = 'pending'` already covers compile jobs.
- Compiles are deliberately **not single-flight** like backtests — several users may be waiting on the model simultaneously.

The daemon executes the stored request verbatim and stores the raw reply in `result_json`; prompt construction and recipe validation stay in the web tier.

## Web Tier: Enqueue and Poll

`apps/web/src/features/recipes/builder/compile-queue.ts` exposes two server functions consumed by the hook:

- `enqueueCompileFn({ data: { messages } })` — meters the request against the daily builder limit via the `consume_builder_compile` RPC (`BUILDER_DAILY_LIMIT = 25`), inserts a `mode='compile'` row with the prepared request in `payload_json`, and returns `{ jobId }`.
- `fetchCompileJobFn({ data: { jobId } })` — reads the job's `status`, `progress_pct`, `result_json`, and `error_message` for the poller.

`apps/web/src/features/recipes/builder/use-builder-chat.ts` drives the lifecycle:

1. `send` appends the user message, then calls `requestCompile`, which enqueues and stores the returned `jobId`. An `inFlight` ref latch prevents a double click from spending two metered compiles.
2. A TanStack Query (`queryKey: ['builder-compile', jobId]`) polls `fetchCompileJobFn` every 2s while the job is `pending` or `processing`, and stops once it reaches a terminal state.
3. When the job settles, the hook parses `result_json.content` with `parseCompilerReply`, validates it with `isCompilerReply`, and calls `finish` exactly once (guarded by a `settledJobId` ref). A malformed or unusable reply degrades to `fallbackReply(UNUSABLE_REPLY)` rather than dead-ending.
4. A failed poll (`job.error`) or a `failed`/`cancelled` job surfaces as a retryable error via `fail`, clearing any stale reply so question buttons do not linger beside a failure message.

The elapsed-time strip counts up from the moment `jobId` is set, not from a boolean `isCompiling` flag.

## Phases

`derivePhase` maps the polled job status onto the builder lifecycle:

| Condition | Phase |
| :--- | :--- |
| `error` set | `error` |
| job `pending` | `queued` |
| job `processing` | `compiling` |
| reply present | `ready` / `question` / `declined` |
| no reply, signed in | `idle` |
| no reply, signed out | `signed-out` |

`isCompiling` is now derived as `Boolean(jobId)`.

## Failure and Fallback Behavior

- **Enqueue refused by the daily meter** — the error surfaces immediately and no job is created.
- **Envelope-less poll** — `assertServerFnResult` throws so the poller keeps the last known state and retries instead of crashing on a property read.
- **Unusable model reply** — the hook drops in the closest starter template (`fallbackReply`) so the visitor still leaves with a runnable bot.
- **Explicit escape hatch** — `useTemplate()` clears the error and finishes with the closest template, never a dead end.

## Related

- [[concepts/recipe-builder-compiler]] — the compiler contract (parse/validate/fallback) the queue feeds
- [[concepts/recipe-builder-usage]] — how visitors drive the builder chat
- [[entities/recipe-studio]] — the builder UI surface
- [[entities/recipe-playground]] — the recipe execution surface sharing the queue
- [[entities/free-llm-proxy]] — the `auto-go` alias the daemon calls for compile jobs
- [[concepts/auto-go-utility-llm]] — the utility-LLM routing the compile request uses
- [[concepts/tanstack-query]] — the polling primitive backing the job query
- [[entities/database]] — the `recipe_execution_queue` table inventory
