-- Create daily_predictions table for S&P Daily Intraday Predictor
CREATE TABLE IF NOT EXISTS public.daily_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_date DATE NOT NULL,
    target_date DATE NOT NULL,
    ticker TEXT NOT NULL DEFAULT 'SPY',
    model_name TEXT NOT NULL,
    prompt_variant_tag TEXT,
    predicted_direction TEXT NOT NULL CHECK (predicted_direction IN ('UP', 'DOWN')),
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    expected_return_pct FLOAT,
    rationale TEXT,
    catalysts JSONB,
    open_price FLOAT,
    close_price FLOAT,
    actual_direction TEXT CHECK (actual_direction IN ('UP', 'DOWN')),
    is_correct BOOLEAN,
    brier_score FLOAT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'evaluated')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Unique constraint per target_date, ticker, model_name
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_predictions_unique
    ON public.daily_predictions(target_date, ticker, model_name);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_daily_predictions_target_date
    ON public.daily_predictions(target_date);
CREATE INDEX IF NOT EXISTS idx_daily_predictions_status
    ON public.daily_predictions(status);

-- RLS Security
ALTER TABLE public.daily_predictions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access on daily_predictions" ON public.daily_predictions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow public read access on daily_predictions" ON public.daily_predictions
    FOR SELECT USING (true);

GRANT SELECT ON public.daily_predictions TO anon, authenticated;
GRANT ALL ON public.daily_predictions TO service_role;
