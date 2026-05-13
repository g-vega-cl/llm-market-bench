-- Add alpaca_filled_at column to trades for fill-timestamp tracking
-- The alpaca_status poller sets this when Alpaca reports the order as FILLED

ALTER TABLE public.trades
ADD COLUMN alpaca_filled_at TIMESTAMPTZ DEFAULT NULL;

COMMENT ON COLUMN public.trades.alpaca_filled_at IS 'Timestamp when the Alpaca order was filled (set by poller).';
