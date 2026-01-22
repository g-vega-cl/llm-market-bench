-- Add realized column to portfolios and portfolio_performance tables
ALTER TABLE public.portfolios ADD COLUMN IF NOT EXISTS realized numeric DEFAULT 10000.00;
ALTER TABLE public.portfolio_performance ADD COLUMN IF NOT EXISTS realized numeric;

COMMENT ON COLUMN public.portfolios.realized IS 'Sum of cash and cost basis of all positions (NLV excluding unrealized PnL).';
COMMENT ON COLUMN public.portfolio_performance.realized IS 'Snapshot of the realized value at the time of snapshot.';
