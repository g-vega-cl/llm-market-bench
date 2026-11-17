-- Public showcase pin for the read-only /recipes-demo page.
--
-- The page used to infer its run from `strategy_recipes.is_public`, but public
-- rows are seeded starter templates that never accrue backtest jobs while every
-- user-cloned recipe stays private, so the preview was permanently empty. One
-- pinned row makes the showcase editorial instead of incidental. A pin that no
-- longer resolves to a completed backtest falls back to the old heuristic, so a
-- stale row degrades to the sign-in card instead of a broken page.

CREATE TABLE IF NOT EXISTS public.recipe_showcase (
    id SMALLINT PRIMARY KEY,
    job_id UUID REFERENCES public.recipe_execution_queue(id) ON DELETE SET NULL,
    recipe_id UUID NOT NULL REFERENCES public.strategy_recipes(id) ON DELETE CASCADE,
    headline TEXT NOT NULL DEFAULT '',
    recipe_name TEXT NOT NULL DEFAULT '',
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT recipe_showcase_single_row CHECK (id = 1)
);

-- Idempotent upgrade for databases that already created the first shape.
ALTER TABLE public.recipe_showcase ADD COLUMN IF NOT EXISTS recipe_name TEXT NOT NULL DEFAULT '';
ALTER TABLE public.recipe_showcase ALTER COLUMN job_id DROP NOT NULL;
ALTER TABLE public.recipe_showcase DROP CONSTRAINT IF EXISTS recipe_showcase_job_id_fkey;
-- A future queue-retention job must degrade the showcase to the fallback
-- heuristic (job_id NULL) instead of deleting the pin row outright.
ALTER TABLE public.recipe_showcase
    ADD CONSTRAINT recipe_showcase_job_id_fkey
    FOREIGN KEY (job_id) REFERENCES public.recipe_execution_queue(id) ON DELETE SET NULL;

COMMENT ON TABLE public.recipe_showcase IS
    'Single pinned backtest (id = 1) rendered by the public /recipes-demo showcase.';

ALTER TABLE public.recipe_showcase ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow service_role full access on recipe_showcase" ON public.recipe_showcase;
CREATE POLICY "Allow service_role full access on recipe_showcase"
    ON public.recipe_showcase FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- The showcase is served exclusively through the service-role server function;
-- visitors never read this table directly.
REVOKE ALL ON public.recipe_showcase FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.recipe_showcase TO service_role;

NOTIFY pgrst, 'reload schema';
