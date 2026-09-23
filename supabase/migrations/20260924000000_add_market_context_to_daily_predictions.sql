-- Migration: Add market_context to daily_predictions for auditing and future model training
ALTER TABLE public.daily_predictions
    ADD COLUMN IF NOT EXISTS market_context TEXT;

COMMENT ON COLUMN public.daily_predictions.market_context IS 'Full pre-market context text (economic prints, options positioning, overnight gaps, newsletters) passed into the predictor model.';
