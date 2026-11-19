---
tags: [recipes, telemetry, scheduler, observability, database]
category: concept
---

# Recipe Ops Telemetry

`public.recipe_ops_events` is durable scheduler/ops telemetry for the recipe runner: enqueue truncation, starved live recipes, and paid-provider fallbacks. Each row carries `event`, `severity` (default `warning`), `detail` (JSONB), and `created_at`, indexed on `created_at DESC`. Service-role only.

## Enqueue Counters

`enqueue_live_recipes_with_stats(sb)` returns a full counter dict rather than a bare count:

| Counter | Meaning |
| :--- | :--- |
| `seen` | Live recipes observed across all pages |
| `enqueued` | Jobs inserted into `recipe_execution_queue` |
| `skipped_open` | Recipes already holding an open job |
| `skipped_invalid_graph` | Recipes whose graph failed strategy validation |

## High-Skip-Ratio Alarm

When more than 10% of seen live recipes are skipped as already-open, the runner inserts a `live_enqueue_high_skip_ratio` event into `recipe_ops_events` with the `seen` count in `detail`. A high skip ratio is a scheduler smell (starvation or duplicate enqueue), not noise.

## Pagination

Live recipes are read in pages of `LIVE_PAGE_SIZE` via `.order(...).range(...)` rather than a single `.limit()`. A single limit silently stopped scheduling recipe 201; pagination must not. The enqueue loop continues until a page returns fewer than `LIVE_PAGE_SIZE` rows.

## Related

- [[concepts/recipe-public-stats]] — the sibling materialised board tables
- [[concepts/observability-standard]] — logging and traceback conventions
- [[entities/recipe-studio]] — the recipe builder UI
- [[entities/database]] — schema and RLS conventions
