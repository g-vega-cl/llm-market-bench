-- Migration: Add intraday hit metrics to daily_predictions
ALTER TABLE public.daily_predictions
    ADD COLUMN IF NOT EXISTS high_price FLOAT,
    ADD COLUMN IF NOT EXISTS low_price FLOAT,
    ADD COLUMN IF NOT EXISTS intraday_hit BOOLEAN,
    ADD COLUMN IF NOT EXISTS intraday_direction_hit BOOLEAN;
