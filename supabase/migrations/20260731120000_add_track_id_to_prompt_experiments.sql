-- Add track_id column to prompt_experiments table to support multi-track AutoResearch
ALTER TABLE public.prompt_experiments
ADD COLUMN IF NOT EXISTS track_id TEXT NOT NULL DEFAULT 'track_default';

-- Create an index for fast track_id lookups
CREATE INDEX IF NOT EXISTS idx_prompt_experiments_track_id
ON public.prompt_experiments(track_id);
