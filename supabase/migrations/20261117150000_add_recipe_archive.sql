-- Soft-hide for Strategy Recipes.
--
-- "Remove from My Strategies" must never delete a row: the isolated paper
-- ledger (paper_cash / paper_positions / paper_trades / paper_equity_curve),
-- the recipe_execution_queue history, and recipe_alerts_inbox all reference it.
-- Archiving only stops the row from being listed, restores it on an explicit
-- Save, cancels its queued jobs, and makes the live scheduler skip it.

ALTER TABLE public.strategy_recipes
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

COMMENT ON COLUMN public.strategy_recipes.archived_at IS
    'Set when the owner removes a strategy from My Strategies. NULL = visible. Rows are never deleted; the paper ledger, queue history, and alerts stay attached. Cleared only by an explicit Save.';

-- Deliberately no new index. The two queries that touch this column are already
-- covered: "My Strategies" is `user_id = ? ORDER BY updated_at DESC`
-- (idx_strategy_recipes_user) and the scheduler is `is_live = TRUE`
-- (idx_strategy_recipes_live). A `(user_id, updated_at DESC) WHERE archived_at
-- IS NULL` index or a second live index would duplicate those with a
-- two-value predicate and only add write amplification on a table that holds
-- tens of rows.
