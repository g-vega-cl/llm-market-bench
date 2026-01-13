-- Add unique constraint to prevent duplicate decisions
-- A decision is unique per: source_id + ticker + signal + model_provider + model_name
-- This enables idempotent upsert operations in the attribution service

-- Step 1: Remove duplicate rows, keeping only the most recent one (by created_at)
DELETE FROM decisions
WHERE id IN (
    SELECT id FROM (
        SELECT
            id,
            ROW_NUMBER() OVER (
                PARTITION BY source_id, ticker, signal, model_provider, model_name
                ORDER BY created_at DESC
            ) AS row_num
        FROM decisions
    ) duplicates
    WHERE row_num > 1
);

-- Step 2: Add the unique constraint
ALTER TABLE decisions
ADD CONSTRAINT unique_decision
UNIQUE (source_id, ticker, signal, model_provider, model_name);
