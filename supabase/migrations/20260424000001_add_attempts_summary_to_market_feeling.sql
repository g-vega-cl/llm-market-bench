-- Add attempts_summary to market_feeling to store rejected trade counts
ALTER TABLE market_feeling ADD COLUMN attempts_summary JSONB;
