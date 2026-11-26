-- Free-text audit note on the Alpaca mirror, deliberately separate from
-- alpaca_status (which carries the order outcome).
--
-- Motivation: the live SPY trader mirrors its ledger order even when the broker
-- holds fewer shares than the ledger is selling (guard_sells=False, so a broker
-- rejection — or a short — is the evidence). That divergence must be visible on
-- the row without overloading the status column.
ALTER TABLE public.trades
ADD COLUMN IF NOT EXISTS alpaca_note TEXT DEFAULT NULL;

COMMENT ON COLUMN public.trades.alpaca_note IS
    'Audit note on the mirror, e.g. BROKER_POSITION_MISMATCH (ledger 2, broker 1). Never used for state.';
