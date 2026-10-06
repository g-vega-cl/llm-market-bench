-- Migration: Create insider trades table
-- Tracks SEC Form 4 insider transactions for corporate officers, directors, and 10%+ owners.

CREATE TABLE IF NOT EXISTS public.insider_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    filing_date DATE NOT NULL,
    transaction_date DATE NOT NULL,
    reporting_name TEXT NOT NULL,
    type_of_owner TEXT,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('purchase', 'sale', 'other')),
    securities_transacted NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    price NUMERIC(14, 4) NOT NULL DEFAULT 0.0000,
    total_value NUMERIC(16, 2) NOT NULL DEFAULT 0.00,
    securities_owned NUMERIC(16, 2),
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_insider_trade UNIQUE (
        symbol, reporting_name, transaction_date, filing_date, transaction_type, securities_transacted, price
    )
);

CREATE INDEX IF NOT EXISTS idx_insider_trades_symbol ON public.insider_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_insider_trades_filing_date ON public.insider_trades(filing_date DESC);
CREATE INDEX IF NOT EXISTS idx_insider_trades_transaction_date ON public.insider_trades(transaction_date DESC);

ALTER TABLE public.insider_trades ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read for insider_trades" ON public.insider_trades
    FOR SELECT USING (true);

CREATE POLICY "Allow service_role full access for insider_trades" ON public.insider_trades
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

GRANT SELECT ON public.insider_trades TO anon, authenticated;
GRANT ALL ON public.insider_trades TO service_role;
