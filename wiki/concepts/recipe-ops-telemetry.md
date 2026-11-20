---
tags: [recipes, telemetry, scheduler, observability, database]
category: concept
---

# Recipe Ops Telemetry

`public.recipe_ops_events` is durable scheduler/ops telemetry for the recipe runner: enqueue truncation, accounting mismatches, starved live recipes, and paid-provider fallbacks. Each row carries `event`, `severity` (default `warning`), `detail` (JSONB), and `created_at`, indexed on `created_at DESC`. Service-role only.

## Enqueue Counters

`enqueue_live_recipes_with_stats(sb)` returns a full counter dict rather than a bare count:

| Counter | Meaning |
| :--- | :--- |
| `seen` | Live recipes observed across all pages |
| `enqueued` | Jobs actually inserted into `recipe_execution_queue` |
| `skipped_open` | Recipes already holding an open job at the slot start |
| `skipped_invalid_graph` | Recipes whose graph failed strategy validation |
| `skipped_recent_turbo` | Recipes skipped because a Turbo turn ran in the 5 minutes before the slot (returned in `detail`, not a dict key) |

`accounted = enqueued + skipped_open + skipped_recent_turbo + skipped_invalid_graph`; anything else is an accounting mismatch and is written as an `error` event carrying the counters plus `accounted`.

## High-Skip-Ratio Alarm

When more than 10% of seen live recipes are skipped as already-open, the runner inserts a `live_enqueue_high_skip_ratio` event into `recipe_ops_events` with the `seen` count in `detail`. A high skip ratio is a scheduler smell (starvation or duplicate enqueue), not noise.

Recent-Turbo skips are deliberately **excluded** from that ratio: a bot that ran a 5-minute Turbo turn seconds before a 30-minute slot is behaving correctly, so counting it as `skipped_open` would page an operator for healthy traffic. `run_scheduled_slot` therefore passes `recent_turbo_cutoff_utc = now - 300s` alongside `slot_start_utc`, and only looks up recent Turbo runs when that cutoff is earlier than the slot start. See [[concepts/recipe-turbo-mode]].

## Idempotent Inserts Under Replica Lag

`_insert_live_jobs_idempotent(sb, jobs)` attempts one batched insert. A `23505` / `duplicate key` failure (the unique partial index `idx_recipe_one_open_live_turn_per_recipe` rejecting a job the read replica had not yet surfaced) falls back to inserting row by row, keeping the successful rows and logging the duplicates at debug level. The returned count is what `enqueued` reports, so the reconciliation stays truthful.

## Pagination

Live recipes are read in pages of `LIVE_PAGE_SIZE` via `.order(...).range(...)` rather than a single `.limit()`. A single limit silently stopped scheduling recipe 201; pagination must not. The enqueue loop continues until a page returns fewer than `LIVE_PAGE_SIZE` rows.

## Public-Stats Pagination

`apps/engine/recipes/public_stats.py` reads the queue with the same discipline, because a PostgREST row cap silently truncates results rather than erroring:

- `_fetch_last_results(sb, recipe_ids)` pages `completed` `live_turn` rows in 500-row windows (up to 10 pages), stopping early once every requested recipe has a result or a short page arrives. A mid-page read error logs and returns whatever it has, so a partial board still refreshes.
- `_count_runs_today(sb, recipe_ids)` pages `completed` `live_turn` rows since midnight UTC in 1,000-row windows until a short page, so `runs_today` on the desk cannot quietly cap at 2,000.

## Related

- [[concepts/recipe-public-stats]] — the sibling materialised board tables these counts feed
- [[concepts/recipe-turbo-mode]] — the 5-minute cadence whose skips are reconciled here
- [[concepts/observability-standard]] — logging and traceback conventions
- [[entities/recipe-studio]] — the recipe builder UI and runner
- [[entities/database]] — schema and RLS conventions
