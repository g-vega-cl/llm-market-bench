-- Add missing Reg T metrics to portfolio_performance table for completeness
alter table public.portfolio_performance 
add column if not exists initial_margin_req numeric,
add column if not exists maintenance_margin_req numeric,
add column if not exists available_funds numeric,
add column if not exists excess_liquidity numeric;
