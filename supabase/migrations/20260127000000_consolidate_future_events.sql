-- Migration to consolidate future_events into memories
-- 1. Add target_date to memories
ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS target_date TEXT;

-- 2. Migrate data from future_events back to memories
-- Each future_event record has a source_memory_id. We update that memory.
UPDATE public.memories m
SET target_date = f.target_date
FROM public.future_events f
WHERE m.id = f.source_memory_id;

-- 3. Add index for target_date performance
CREATE INDEX IF NOT EXISTS memories_target_date_idx ON public.memories (target_date) WHERE target_date IS NOT NULL;

-- 4. Drop the redundant future_events table
DROP TABLE IF EXISTS public.future_events;
