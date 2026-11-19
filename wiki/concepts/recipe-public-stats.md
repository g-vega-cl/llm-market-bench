---
tags: [recipes, leaderboard, materialized-views, zero-frontend-compute, database]
category: concept
---

# Recipe Public Stats

The recipe desk's public homepage is backed by **runner-materialised tables** rather than browser-side computation. The recipe runner writes one row per live recipe into `public.recipe_public_stats` each cycle, plus a single-row `public.recipe_desk_summary` header and a `public.recipe_desk_feed` tape of same-day executed signals. The frontend reads these tables directly, honoring the repo's [[concepts/zero-frontend-compute]] mandate — no parsing of `strategy_recipes.paper_equity_curve` in the browser.

## Tables

### `public.recipe_public_stats`
One row per recipe (`recipe_id` PK, `ON DELETE CASCADE`). Columns: `name`, `is_live`, `return_pct`, `spy_return_pct`, `trade_count`, `open_positions`, `runs_today`, `first_equity_date`, `last_equity_date`, `last_run_at`, `last_action` (JSONB), `resolved_model`, `updated_at`. Indexed on `last_run_at DESC WHERE is_live = true`. Public read via RLS; service_role full access.

### `public.recipe_desk_summary`
Single-row (`id = 1` CHECK) header: `live_count`, `beat_spy_count`, `median_return_pct`, `updated_at`. Public read.

### `public.recipe_desk_feed`
Materialised same-day tape of executed signals: `recipe_id`, `recipe_name`, `action`, `ticker`, `at`, `created_at`. Indexed on `at DESC`. Public read.

## Builder (`apps/engine/recipes/runner.py`)

- `parse_equity_curve(curve)` — extracts `(date, equity)` pairs, skipping unreadable labels and null equity.
- `return_pct(curve)` — first-to-last point return; `None` for empty or single-point curves; negative values survive (losers are published).
- `spy_return_pct(rows, start, end)` — matching-window SPY closes; `None` without a matching start close.
- `build_last_action(result)` — first executed signal, normalised ticker, whitespace-collapsed reason.
- `build_public_stats(recipe, spy_rows, last_job_result, runs_today, resolved_model)` — assembles the row.
- `refresh_public_stats(client)` — upserts one row per live recipe and prunes stale rows; returns `{live_recipes, rows_written, rows_pruned}`.

`run_scheduled_slot` calls `refresh_public_stats(sb)` after draining the lane. A stats-refresh failure is caught and logged — a board write must never abort the trading cycle.

## Related

- [[concepts/zero-frontend-compute]] — the mandate these tables satisfy
- concepts/recipe-ops-telemetry — the sibling durable ops table
- [[entities/recipe-studio]] — the recipe builder UI
- [[entities/recipe-live-status]] — live recipe status surface
- [[entities/database]] — schema and RLS conventions
