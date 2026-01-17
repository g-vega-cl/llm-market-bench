-- Create portfolios table
create table if not exists public.portfolios (
    id uuid primary key default gen_random_uuid(),
    owner_id text not null unique, -- 'gpt-4o', 'claude-3-5-sonnet', etc.
    cash_balance numeric not null default 10000.00,
    
    -- Reg T Metrics
    total_equity numeric,        -- Net Liquidation Value (NLV)
    buying_power numeric,        -- Intraday Buying Power (4x Excess)
    excess_liquidity numeric,    -- Excess over margin req
    maintenance_margin numeric,  -- Current maintenance margin req
    
    last_updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create portfolio_positions table
create table if not exists public.portfolio_positions (
    id uuid primary key default gen_random_uuid(),
    portfolio_id uuid not null references public.portfolios(id) on delete cascade,
    ticker text not null,
    quantity int not null,
    average_cost_basis numeric not null,
    
    -- Ensure one row per ticker per portfolio
    unique(portfolio_id, ticker),
    constraint quantity_not_negative check (quantity >= 0)
);

-- Enable RLS (Row Level Security) - though primarily used by engine service role for now
alter table public.portfolios enable row level security;
alter table public.portfolio_positions enable row level security;

-- Policies (optional for now, as engine uses service key, but good practice)
create policy "Enable read access for all users" on public.portfolios for select using (true);
create policy "Enable read access for all users" on public.portfolio_positions for select using (true);
