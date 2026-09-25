-- Migration: Add postmortem fields to daily_predictions
ALTER TABLE public.daily_predictions
    ADD COLUMN IF NOT EXISTS postmortem_category TEXT,
    ADD COLUMN IF NOT EXISTS postmortem_flawed_assumption TEXT,
    ADD COLUMN IF NOT EXISTS postmortem_lesson TEXT,
    ADD COLUMN IF NOT EXISTS was_predictable BOOLEAN,
    ADD COLUMN IF NOT EXISTS postmortem_evaluated_at TIMESTAMPTZ;

COMMENT ON COLUMN public.daily_predictions.postmortem_category IS 'Diagnosed error taxonomy from GPT-5.6 Luna post-mortem (e.g. ACCURATE_CAPTURE, TIMID_MAGNITUDE, CATALYST_INVERSION, UNFORESEEN_SHOCK).';
COMMENT ON COLUMN public.daily_predictions.postmortem_flawed_assumption IS 'Specific assumption or reasoning flaw identified from morning rationale.';
COMMENT ON COLUMN public.daily_predictions.postmortem_lesson IS 'Durable rule extracted from daily outcome to feed weekly autoresearch.';
COMMENT ON COLUMN public.daily_predictions.was_predictable IS 'True if the failure mode was predictable from pre-market signals; False for random chop or mid-day shocks.';
COMMENT ON COLUMN public.daily_predictions.postmortem_evaluated_at IS 'Timestamp when the daily post-mortem was completed by GPT-5.6 Luna.';
