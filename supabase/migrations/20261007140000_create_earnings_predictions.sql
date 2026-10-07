-- Migration: Create earnings_predictions table for Day-1 Earnings Movement Predictor Arena
-- Benchmarks LLMs (GPT Luna, DeepSeek Flash, TypeSafe Jev) on predicting Day-1 RTH Open-to-Close (UP/DOWN) direction.

CREATE TABLE IF NOT EXISTS public.earnings_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_date DATE NOT NULL,
    target_date DATE NOT NULL,
    ticker TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_variant_tag TEXT,
    predicted_direction TEXT NOT NULL CHECK (predicted_direction IN ('UP', 'DOWN')),
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    expected_return_pct FLOAT,
    rationale TEXT,
    catalysts JSONB DEFAULT '[]'::jsonb,
    report_timing TEXT DEFAULT 'BMO' CHECK (report_timing IN ('BMO', 'AMC', 'UNKNOWN')),
    actual_eps NUMERIC,
    estimated_eps NUMERIC,
    eps_surprise NUMERIC,
    revenue_surprise_pct NUMERIC,
    sue_score NUMERIC,
    open_price FLOAT,
    close_price FLOAT,
    actual_direction TEXT CHECK (actual_direction IN ('UP', 'DOWN')),
    is_correct BOOLEAN,
    brier_score FLOAT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'evaluated')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_earnings_predictions UNIQUE (target_date, ticker, model_name)
);

CREATE INDEX IF NOT EXISTS idx_earnings_pred_target_date ON public.earnings_predictions(target_date DESC);
CREATE INDEX IF NOT EXISTS idx_earnings_pred_status ON public.earnings_predictions(status);
CREATE INDEX IF NOT EXISTS idx_earnings_pred_ticker ON public.earnings_predictions(ticker);
CREATE INDEX IF NOT EXISTS idx_earnings_pred_model ON public.earnings_predictions(model_name);

ALTER TABLE public.earnings_predictions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access on earnings_predictions" ON public.earnings_predictions
    FOR SELECT USING (true);

CREATE POLICY "Service role full access on earnings_predictions" ON public.earnings_predictions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

GRANT SELECT ON public.earnings_predictions TO anon, authenticated;
GRANT ALL ON public.earnings_predictions TO service_role;
