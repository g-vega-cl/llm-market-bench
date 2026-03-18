-- Add realized_pnl and realized_pnl_pct to trades table
ALTER TABLE public.trades 
ADD COLUMN realized_pnl NUMERIC DEFAULT NULL,
ADD COLUMN realized_pnl_pct NUMERIC DEFAULT NULL;

COMMENT ON COLUMN public.trades.realized_pnl IS 'The profit or loss realized by this trade (for SELL signals).';
COMMENT ON COLUMN public.trades.realized_pnl_pct IS 'The profit or loss percentage realized by this trade.';
