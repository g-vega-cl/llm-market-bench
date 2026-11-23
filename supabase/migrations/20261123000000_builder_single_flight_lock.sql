-- ============================================================================
-- Migration: 20261123000000_builder_single_flight_lock.sql
-- Description: Enforce an atomic per-user single-flight concurrency lock for
--              /build compile jobs so concurrent requests cannot race past the
--              application-level in-flight check.
-- ============================================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_recipe_one_pending_compile_per_user
    ON public.recipe_execution_queue (user_id)
    WHERE mode = 'compile' AND status IN ('pending', 'processing');

COMMENT ON INDEX public.idx_recipe_one_pending_compile_per_user IS
    'A user can have at most one pending or processing /build compile job at a time.';
