-- Migration: Create congress trades table
-- Tracks STOCK Act stock transaction disclosures for US Senate and House of Representatives.

CREATE TABLE IF NOT EXISTS public.congress_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chamber TEXT NOT NULL CHECK (chamber IN ('senate', 'house')),
    symbol TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    disclosure_date DATE NOT NULL,
    representative_name TEXT NOT NULL,
    district TEXT,
    owner TEXT,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('purchase', 'sale', 'exchange')),
    amount_range TEXT NOT NULL,
    amount_est_midpoint NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    asset_description TEXT,
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_congress_trade UNIQUE (
        chamber, representative_name, symbol, transaction_date, transaction_type, amount_range
    )
);

CREATE INDEX IF NOT EXISTS idx_congress_trades_symbol ON public.congress_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_congress_trades_disclosure_date ON public.congress_trades(disclosure_date DESC);
CREATE INDEX IF NOT EXISTS idx_congress_trades_transaction_date ON public.congress_trades(transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_congress_trades_chamber ON public.congress_trades(chamber);

ALTER TABLE public.congress_trades ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read for congress_trades" ON public.congress_trades
    FOR SELECT USING (true);

CREATE POLICY "Allow service_role full access for congress_trades" ON public.congress_trades
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

GRANT SELECT ON public.congress_trades TO anon, authenticated;
GRANT ALL ON public.congress_trades TO service_role;
