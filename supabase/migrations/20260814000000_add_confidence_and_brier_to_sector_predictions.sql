-- Add confidence and brier_score columns to sector_predictions table
ALTER TABLE public.sector_predictions
ADD COLUMN IF NOT EXISTS confidence FLOAT CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 100)),
ADD COLUMN IF NOT EXISTS brier_score FLOAT;
