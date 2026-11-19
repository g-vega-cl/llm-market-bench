-- ============================================================================
-- Migration: 20261119010000_recipe_one_processing_backtest_per_recipe.sql
-- Description: With three concurrent backtests allowed, the 10-minute heartbeat
--              reclaim could re-queue a slow-but-live backtest while it is still
--              running, and two workers would then write the same recipe's
--              paper ledger. A per-recipe partial unique index makes the double
--              run impossible without capping the global lane.
-- ============================================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_recipe_one_processing_backtest_per_recipe
    ON public.recipe_execution_queue (recipe_id)
    WHERE mode = 'backtest' AND status = 'processing';

COMMENT ON INDEX public.idx_recipe_one_processing_backtest_per_recipe IS
    'A recipe can never have two in-flight backtests, even after a heartbeat reclaim.';
