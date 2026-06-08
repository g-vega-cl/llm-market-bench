-- Migration to add support for multi-window trailing returns and correlations: 7-day, 30-day, and 60-day.
-- The existing columns (pearson_corr, spearman_corr, returns_a_90d, returns_b_90d) are retained for 90-day data.

ALTER TABLE correlation_data
ADD COLUMN returns_a_7d FLOAT,
ADD COLUMN returns_b_7d FLOAT,
ADD COLUMN returns_a_30d FLOAT,
ADD COLUMN returns_b_30d FLOAT,
ADD COLUMN returns_a_60d FLOAT,
ADD COLUMN returns_b_60d FLOAT,
ADD COLUMN pearson_corr_7d FLOAT,
ADD COLUMN spearman_corr_7d FLOAT,
ADD COLUMN pearson_corr_30d FLOAT,
ADD COLUMN spearman_corr_30d FLOAT,
ADD COLUMN pearson_corr_60d FLOAT,
ADD COLUMN spearman_corr_60d FLOAT;

-- Comments on the new columns for documentation clarity
COMMENT ON COLUMN correlation_data.returns_a_7d IS '7-day trailing return for ticker_a (percentage)';
COMMENT ON COLUMN correlation_data.returns_b_7d IS '7-day trailing return for ticker_b (percentage)';
COMMENT ON COLUMN correlation_data.returns_a_30d IS '30-day trailing return for ticker_a (percentage)';
COMMENT ON COLUMN correlation_data.returns_b_30d IS '30-day trailing return for ticker_b (percentage)';
COMMENT ON COLUMN correlation_data.returns_a_60d IS '60-day trailing return for ticker_a (percentage)';
COMMENT ON COLUMN correlation_data.returns_b_60d IS '60-day trailing return for ticker_b (percentage)';

COMMENT ON COLUMN correlation_data.pearson_corr_7d IS '7-day Pearson correlation coefficient (-1 to 1)';
COMMENT ON COLUMN correlation_data.spearman_corr_7d IS '7-day Spearman rank correlation coefficient (-1 to 1)';
COMMENT ON COLUMN correlation_data.pearson_corr_30d IS '30-day Pearson correlation coefficient (-1 to 1)';
COMMENT ON COLUMN correlation_data.spearman_corr_30d IS '30-day Spearman rank correlation coefficient (-1 to 1)';
COMMENT ON COLUMN correlation_data.pearson_corr_60d IS '60-day Pearson correlation coefficient (-1 to 1)';
COMMENT ON COLUMN correlation_data.spearman_corr_60d IS '60-day Spearman rank correlation coefficient (-1 to 1)';
