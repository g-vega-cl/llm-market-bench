-- Add actual return and benchmark return columns to sector_predictions table
ALTER TABLE public.sector_predictions
    ADD COLUMN IF NOT EXISTS predicted_sector_return FLOAT,
    ADD COLUMN IF NOT EXISTS predicted_pair_return FLOAT,
    ADD COLUMN IF NOT EXISTS benchmark_spy_return FLOAT;
