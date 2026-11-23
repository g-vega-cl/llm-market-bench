---
tags: [recipes, rate-limiting, builder, database, security, single-flight]
category: concept
---

# Recipe Builder Usage

`public.recipe_builder_usage` enforces a per-user daily cap on `/build` compiles, which spend real proxy tokens. The table is keyed on `(user_id, usage_day)` with a `compiles` counter and `updated_at`.

## Atomic Spend

`consume_builder_compile(p_user UUID)` atomically increments the day's counter and returns the running total, so two concurrent requests can never both slip under the cap:

```sql
INSERT INTO public.recipe_builder_usage (user_id, usage_day, compiles)
VALUES (p_user, (NOW() AT TIME ZONE 'utc')::date, 1)
ON CONFLICT (user_id, usage_day)
DO UPDATE SET compiles = public.recipe_builder_usage.compiles + 1,
              updated_at = NOW()
RETURNING compiles INTO new_count;
```

The function is `SECURITY DEFINER`, revoked from `PUBLIC`/`anon`/`authenticated`, and granted only to `service_role`.

## Cap and Consumer

The cap is `BUILDER_DAILY_LIMIT = 25` compiles per user per day, exported by `apps/web/src/features/recipes/builder/compile-queue.ts`. The spend moved with the work: `enqueueCompileFn` only pre-checks `recipe_builder_usage`, while the recipes daemon calls `consume_builder_compile` **immediately before** it contacts `free-llm-proxy` — so a job that never runs (daemon down) costs nothing, and a throttled request still never spends model tokens. When the returned counter exceeds 25 the job fails with a message pointing the user at editing an existing recipe. The spend is per compile attempt against the model, not per successful recipe — a compile that produces a clarifying question still counts. See [[concepts/recipe-compile-queue]] and [[concepts/recipe-builder-compiler]].

## Enqueue-Side Concurrency Guards

The daily meter is the *budget*; two cheaper guards keep a user from fanning out requests that would each spend it:

- **Single-flight (`MAX_PENDING_COMPILES = 1`)** — `enqueueCompile` counts the caller's `mode='compile'` rows in `pending`/`processing` and refuses with `pendingCompilesMessage()` when one is already in flight. The check is backed at the storage layer by the partial unique index `idx_recipe_one_pending_compile_per_user` (migration `20261123000000_builder_single_flight_lock.sql`), so a read-then-insert race surfaces as SQLSTATE `23505` and is mapped to the same message instead of a raw database error.
- **Burst window (`BUILDER_BURST_LIMIT = 5` per `BUILDER_BURST_WINDOW_MINUTES = 5`)** — `enqueueCompile` counts the caller's compile rows created in the last five minutes and refuses with `builderBurstLimitMessage()` at the limit. This bounds a rapid-fire loop that would otherwise stay under the daily meter while still spending provider tokens.

Both guards are pre-checks only: they never spend the meter, and a job that is refused or abandoned costs nothing.

## Server-Locked Request

The row a user enqueues cannot become an arbitrary LLM proxy call. `buildCompilePayload()` fixes `model: 'auto-go'`, `max_tokens: COMPILE_MAX_TOKENS` (1600), `temperature: 0.2`, and `response_format: { type: 'json_object' }`, and the worker re-locks all four through `_sanitize_compile_payload` before spending the meter — so a tampered `payload_json` fails the job without a provider call. See [[concepts/recipe-compile-queue]].

## No Public API Surface

PostgREST's default privileges let `anon`/`authenticated` hold table SELECT on new public tables. RLS then filters every row, so the API answered `200 []` instead of `403` — no data leaked, but the table was advertised on the public API surface. A follow-up migration revokes all grants from `anon`/`authenticated` so the endpoint returns `401/403`. The table is service-role only.

## Related

- [[concepts/recipe-builder-compiler]] — the `/build` compiler that spends this allowance
- [[concepts/recipe-compile-queue]] — the queue, single-flight index, and payload lock
- [[concepts/recipe-public-stats]] — the public board tables
- [[concepts/rls-enforcement-standard]] — row-level security conventions
- [[concepts/supabase-grant-convention]] — grant/revoke conventions
- [[entities/recipe-studio]] — the recipe builder UI
