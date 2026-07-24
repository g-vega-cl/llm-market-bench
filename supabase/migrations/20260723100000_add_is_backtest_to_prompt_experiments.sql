-- Add is_backtest column to prompt_experiments table to support backtest runs
ALTER TABLE public.prompt_experiments
ADD COLUMN IF NOT EXISTS is_backtest BOOLEAN NOT NULL DEFAULT false;

-- Create an index to quickly filter live vs backtest runs
CREATE INDEX IF NOT EXISTS idx_prompt_experiments_is_backtest
ON public.prompt_experiments(is_backtest);
