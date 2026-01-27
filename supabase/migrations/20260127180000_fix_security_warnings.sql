-- Migration: Fix Supabase Security Warnings
-- Description: Sets position_pnl view to SECURITY INVOKER and enables RLS on price_history.
-- Created: 2026-01-27

-- 1. Update position_pnl to use security_invoker
-- Note: Re-creating the view with explicit security_invoker = true
DROP VIEW IF EXISTS public.position_pnl;

CREATE VIEW public.position_pnl 
WITH (security_invoker = true)
AS
SELECT 
    p.id as position_id,
    p.portfolio_id,
    port.owner_id,
    p.ticker,
    p.quantity,
    p.average_cost_basis,
    m.price AS current_price,
    m.fetched_at AS price_fetched_at,
    (COALESCE(m.price, p.average_cost_basis) - p.average_cost_basis) * p.quantity AS unrealized_pnl_usd,
    CASE 
        WHEN p.average_cost_basis > 0 THEN ((COALESCE(m.price, p.average_cost_basis) / p.average_cost_basis) - 1) * 100 
        ELSE 0 
    END AS unrealized_pnl_pct
FROM 
    public.portfolio_positions p
JOIN
    public.portfolios port ON p.portfolio_id = port.id
LEFT JOIN 
    public.market_data_cache m ON p.ticker = m.ticker;

-- Re-grant access
ALTER VIEW public.position_pnl OWNER TO postgres;
GRANT SELECT ON public.position_pnl TO anon, authenticated, service_role;

-- 2. Enable RLS on price_history
ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;

-- Allow read access for all (consistent with market_data_cache and trades)
CREATE POLICY "Allow read access for all on price_history" 
    ON public.price_history FOR SELECT 
    USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role full access to price_history" 
    ON public.price_history FOR ALL 
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Update comments
COMMENT ON VIEW public.position_pnl IS 'Dynamically calculates unrealized P&L. SECURITY INVOKER enabled.';
COMMENT ON TABLE public.price_history IS 'Stores a historical record of stock prices. RLS enabled.';
