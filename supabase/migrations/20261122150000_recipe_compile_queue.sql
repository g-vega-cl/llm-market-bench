-- ============================================================================
-- /build compile jobs on the shared recipe queue.
--
--   1. recipe_execution_queue.recipe_id becomes nullable — a compile has no
--      recipe; it carries its own conversation payload.
--   2. payload_json holds the prepared auto-go request (built server-side by the
--      web app, so the model contract stays in one language).
--   3. mode gains 'compile' so the 5s daemon picks these up like any other job.
--
-- The daemon executes the stored request verbatim and stores the raw reply;
-- prompt construction and recipe validation stay in the web tier (TS).
-- ============================================================================

ALTER TABLE public.recipe_execution_queue
    ALTER COLUMN recipe_id DROP NOT NULL;

ALTER TABLE public.recipe_execution_queue
    ADD COLUMN IF NOT EXISTS payload_json JSONB;

-- Recreate the mode check without assuming its generated name (the earlier
-- quota migration used the same drop-and-recreate pattern).
DO $$
DECLARE
    chk RECORD;
BEGIN
    FOR chk IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'public.recipe_execution_queue'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%mode%'
    LOOP
        EXECUTE format('ALTER TABLE public.recipe_execution_queue DROP CONSTRAINT %I', chk.conname);
    END LOOP;
END $$;

ALTER TABLE public.recipe_execution_queue
    ADD CONSTRAINT recipe_execution_queue_mode_check
    CHECK (mode IN ('preview', 'backtest', 'live_turn', 'compile'));

-- The pickup index is already (mode, priority, created_at) WHERE status='pending',
-- which covers compile. Compiles are deliberately NOT single-flight like backtests:
-- several users may wait on the model at once.

COMMENT ON COLUMN public.recipe_execution_queue.payload_json IS
    'Prepared request body for mode=compile jobs (auto-go chat completion); null for recipe jobs.';
COMMENT ON COLUMN public.recipe_execution_queue.recipe_id IS
    'Owning recipe for backtest/live_turn/preview jobs; null for mode=compile.';
