-- Add SMA (Special Memorandum Account) column to portfolios table
-- This tracks the stateful "Buying Power Line of Credit" that doesn't drop with market loss.

ALTER TABLE portfolios 
ADD COLUMN IF NOT EXISTS sma numeric DEFAULT 0.0;

COMMENT ON COLUMN portfolios.sma IS 'Special Memorandum Account: Preserves buying power during market drawdowns.';
