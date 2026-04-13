-- Add reasoning column to trades table for system-generated trade reasoning (dust cleanup, etc.)
ALTER TABLE public.trades 
ADD COLUMN reasoning TEXT DEFAULT NULL;

COMMENT ON COLUMN public.trades.reasoning IS 'Optional reasoning field for system-generated trades or additional context.';
