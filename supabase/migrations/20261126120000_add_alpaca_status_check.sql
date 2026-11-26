-- Enforce the valid discrete states for trades.alpaca_status and index repair/sync queries.
-- Matches all runtime and historical states documented in wiki/concepts/state-machines.md.

ALTER TABLE public.trades
    DROP CONSTRAINT IF EXISTS trades_alpaca_status_check;

ALTER TABLE public.trades
    ADD CONSTRAINT trades_alpaca_status_check
    CHECK (
        alpaca_status IS NULL
        OR alpaca_status IN (
            'SUBMITTED',
            'FILLED',
            'CANCELED',
            'EXPIRED',
            'REJECTED',
            'ERROR',
            'BACKFILLED',
            'SKIPPED_NO_POSITION',
            'DISABLED',
            'NO_MIRROR'
        )
    ) NOT VALID;

ALTER TABLE public.trades
    VALIDATE CONSTRAINT trades_alpaca_status_check;

CREATE INDEX IF NOT EXISTS trades_alpaca_repair_idx
    ON public.trades (executed_at DESC)
    WHERE alpaca_status IS NULL OR alpaca_status = 'ERROR';

CREATE INDEX IF NOT EXISTS trades_alpaca_submitted_idx
    ON public.trades (alpaca_submitted_at)
    WHERE alpaca_status = 'SUBMITTED';

COMMENT ON COLUMN public.trades.alpaca_status IS
    'Alpaca mirror status: SUBMITTED, FILLED, CANCELED, EXPIRED, REJECTED, ERROR, BACKFILLED, SKIPPED_NO_POSITION, DISABLED, NO_MIRROR (or NULL if not mirrored).';

NOTIFY pgrst, 'reload schema';
