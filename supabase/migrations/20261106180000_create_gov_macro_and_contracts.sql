-- Migration: Create gov macro liquidity and gov contracts tables
-- Tracks US & Canadian government spending, Treasury General Account cash balances,
-- national debt, deficits, and government procurement/contract awards.

CREATE TABLE IF NOT EXISTS public.gov_macro_liquidity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_date DATE NOT NULL UNIQUE,
    tga_balance NUMERIC(18, 2),
    tot_pub_debt NUMERIC(18, 2),
    debt_held_public NUMERIC(18, 2),
    intragov_holdings NUMERIC(18, 2),
    monthly_deficit_surplus NUMERIC(18, 2),
    raw_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gov_macro_liquidity_record_date 
    ON public.gov_macro_liquidity(record_date DESC);

ALTER TABLE public.gov_macro_liquidity ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read for gov_macro_liquidity" ON public.gov_macro_liquidity
    FOR SELECT USING (true);

CREATE POLICY "Allow service_role full access for gov_macro_liquidity" ON public.gov_macro_liquidity
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

GRANT SELECT ON public.gov_macro_liquidity TO anon, authenticated;
GRANT ALL ON public.gov_macro_liquidity TO service_role;


CREATE TABLE IF NOT EXISTS public.gov_contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country TEXT NOT NULL CHECK (country IN ('US', 'CA', 'OTHER')),
    award_id TEXT NOT NULL,
    recipient_name TEXT NOT NULL,
    award_amount NUMERIC(16, 2) NOT NULL DEFAULT 0.00,
    currency TEXT NOT NULL DEFAULT 'USD',
    description TEXT,
    agency_name TEXT,
    award_date DATE NOT NULL,
    contract_number TEXT,
    source_url TEXT,
    raw_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_gov_contracts UNIQUE (country, award_id, recipient_name, award_date)
);

CREATE INDEX IF NOT EXISTS idx_gov_contracts_country_date 
    ON public.gov_contracts(country, award_date DESC);
CREATE INDEX IF NOT EXISTS idx_gov_contracts_recipient 
    ON public.gov_contracts(recipient_name);
CREATE INDEX IF NOT EXISTS idx_gov_contracts_amount 
    ON public.gov_contracts(award_amount DESC);

ALTER TABLE public.gov_contracts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read for gov_contracts" ON public.gov_contracts
    FOR SELECT USING (true);

CREATE POLICY "Allow service_role full access for gov_contracts" ON public.gov_contracts
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

GRANT SELECT ON public.gov_contracts TO anon, authenticated;
GRANT ALL ON public.gov_contracts TO service_role;
