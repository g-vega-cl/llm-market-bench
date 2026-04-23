-- Add Alpaca audit columns to trades table
-- Supabase is the source of truth. Alpaca is a fire-and-forget audit mirror.

ALTER TABLE public.trades
ADD COLUMN alpaca_order_id TEXT DEFAULT NULL,
ADD COLUMN alpaca_status TEXT DEFAULT NULL,
ADD COLUMN alpaca_submitted_at TIMESTAMPTZ DEFAULT NULL;

COMMENT ON COLUMN public.trades.alpaca_order_id IS 'Alpaca order UUID for third-party audit trail.';
COMMENT ON COLUMN public.trades.alpaca_status IS 'Alpaca order status: PENDING, FILLED, REJECTED, ERROR.';
COMMENT ON COLUMN public.trades.alpaca_submitted_at IS 'Timestamp when the order was submitted to Alpaca.';