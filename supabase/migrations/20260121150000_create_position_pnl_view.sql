-- Create a public view to calculate P&L dynamically.
-- This compares the latest price in market_data_cache with the average_cost_basis in portfolio_positions.

CREATE OR REPLACE VIEW public.position_pnl AS
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

-- Grant access to the view
ALTER VIEW public.position_pnl OWNER TO postgres;
GRANT SELECT ON public.position_pnl TO anon, authenticated, service_role;

COMMENT ON VIEW public.position_pnl IS 'Dynamically calculates unrealized P&L for all portfolio positions based on cached market data.';
