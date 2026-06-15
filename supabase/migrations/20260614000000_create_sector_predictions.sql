-- Create sector_predictions table for the Model Arena

CREATE TABLE IF NOT EXISTS public.sector_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_date DATE NOT NULL,
    target_date DATE NOT NULL,
    timeframe TEXT NOT NULL CHECK (timeframe IN ('7d', '30d', '60d', '90d')),
    model_name TEXT NOT NULL,
    prompt_tag TEXT,
    predicted_sector TEXT NOT NULL,
    predicted_pair JSONB NOT NULL,
    reasoning TEXT,
    sector_percentile_score FLOAT,
    pair_percentile_score FLOAT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'evaluated')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indices for fast querying
CREATE INDEX IF NOT EXISTS idx_sector_predictions_target_date
    ON sector_predictions(target_date);
CREATE INDEX IF NOT EXISTS idx_sector_predictions_timeframe
    ON sector_predictions(timeframe);
CREATE INDEX IF NOT EXISTS idx_sector_predictions_model_name
    ON sector_predictions(model_name);

-- RLS
ALTER TABLE public.sector_predictions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access" ON public.sector_predictions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Allow public read access" ON public.sector_predictions
    FOR SELECT USING (true);
