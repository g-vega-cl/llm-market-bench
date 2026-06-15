-- Deduplicate sector_predictions table by keeping only the latest prediction for each prediction_date, model_name, and timeframe
DELETE FROM public.sector_predictions
WHERE id NOT IN (
    SELECT DISTINCT ON (prediction_date, model_name, timeframe) id
    FROM public.sector_predictions
    ORDER BY prediction_date, model_name, timeframe, created_at DESC
);

-- Add unique constraint to sector_predictions
ALTER TABLE public.sector_predictions
ADD CONSTRAINT unique_prediction_date_model_timeframe UNIQUE (prediction_date, model_name, timeframe);
