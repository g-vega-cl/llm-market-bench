-- Create prompt_experiments table for auto-research prompt versioning
CREATE TABLE IF NOT EXISTS public.prompt_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_tag TEXT NOT NULL UNIQUE,
    prompt_name TEXT NOT NULL DEFAULT 'CORE_ANALYSIS_SYSTEM_PROMPT',
    prompt_content TEXT NOT NULL,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    metrics JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'kept', 'discarded', 'crashed')),
    experiment_type TEXT NOT NULL DEFAULT 'incremental'
        CHECK (experiment_type IN ('incremental', 'radical', 'baseline')),
    parent_tag TEXT REFERENCES prompt_experiments(variant_tag),
    change_description TEXT,
    research_output JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prompt_experiments_active
    ON prompt_experiments(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_prompt_experiments_week
    ON prompt_experiments(week_start);

ALTER TABLE public.prompt_experiments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access" ON public.prompt_experiments
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow public read access" ON public.prompt_experiments
    FOR SELECT USING (true);
