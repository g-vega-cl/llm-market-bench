-- Add worst sector prediction, returns, and scores to sector_predictions table
ALTER TABLE public.sector_predictions
ADD COLUMN IF NOT EXISTS predicted_worst_sector TEXT,
ADD COLUMN IF NOT EXISTS worst_sector_percentile_score FLOAT,
ADD COLUMN IF NOT EXISTS predicted_worst_sector_return FLOAT,
ADD COLUMN IF NOT EXISTS sector_sp_diff FLOAT;
