-- Migration to update prompt_experiments table status constraint
-- 1. Drop existing check constraint if it exists.
ALTER TABLE public.prompt_experiments DROP CONSTRAINT IF EXISTS prompt_experiments_status_check;

-- 2. Update existing 'kept' variants to 'baseline' if they are the highest scoring for their prompt_name.
UPDATE public.prompt_experiments
SET status = 'baseline'
WHERE id IN (
    SELECT DISTINCT ON (prompt_name) id
    FROM public.prompt_experiments
    WHERE status = 'kept'
    ORDER BY prompt_name, (metrics->>'score')::numeric DESC NULLS LAST, created_at DESC
);

-- 3. Update any remaining 'kept' variants to 'saved'.
UPDATE public.prompt_experiments
SET status = 'saved'
WHERE status = 'kept';

-- 4. Add the new check constraint allowing 'active', 'baseline', 'saved', 'discarded', 'crashed'.
ALTER TABLE public.prompt_experiments
ADD CONSTRAINT prompt_experiments_status_check
CHECK (status IN ('active', 'baseline', 'saved', 'discarded', 'crashed'));
