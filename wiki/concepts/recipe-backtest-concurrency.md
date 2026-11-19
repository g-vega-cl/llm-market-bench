---
tags: [recipes, concurrency, backtest, scheduler, database]
category: concept
---

# Recipe Backtest Concurrency

The recipe execution lane allows **three concurrent backtests** instead of one. The previous unique `((1))` index physically forbade a second `processing` backtest; a counted guard inside the existing advisory lock replaces it.

## Dequeue Guard

`pop_next_recipe_job(target_mode TEXT DEFAULT NULL)`:

1. Takes `pg_advisory_xact_lock(hashtext('recipe_backtest_dequeue_lock'))` when `target_mode` is null or `backtest`, so dequeue stays serialised — no two workers observe the same vacant slot.
2. Reclaims stalled jobs whose `COALESCE(heartbeat_at, started_at)` lapsed more than 10 minutes, resetting them to `pending`.
3. Counts `processing` backtests and returns early when `target_mode = 'backtest'` and the count is at `c_max_processing_backtests = 3`.
4. Selects the next pending job with `FOR UPDATE SKIP LOCKED`, respecting the backtest cap, and marks it `processing` with `progress_pct = 5`.

## Per-Recipe Guard

With three concurrent backtests allowed, the 10-minute heartbeat reclaim could re-queue a slow-but-live backtest while it is still running, and two workers would then write the same recipe's paper ledger. A partial unique index makes the double run impossible without capping the global lane:

```sql
CREATE UNIQUE INDEX idx_recipe_one_processing_backtest_per_recipe
    ON public.recipe_execution_queue (recipe_id)
    WHERE mode = 'backtest' AND status = 'processing';
```

## Lane Drain

`drain_lane(..., mode='backtest', max_jobs=3)` runs up to three jobs concurrently. A serial lane would deadlock the three-concurrent promise.

## Related

- [[concepts/recipe-public-stats]] — the board refreshed after each slot
- [[concepts/recipe-ops-telemetry]] — scheduler health events
- [[entities/recipe-studio]] — the recipe builder UI
- [[entities/database]] — schema and RLS conventions
