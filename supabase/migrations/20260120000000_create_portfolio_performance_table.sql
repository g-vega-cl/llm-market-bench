-- Create portfolio_performance table for daily snapshots
create table if not exists public.portfolio_performance (
    id uuid primary key default gen_random_uuid(),
    portfolio_id uuid not null references public.portfolios(id) on delete cascade,
    date date not null default current_date,
    
    -- Metrics Snapshot
    total_equity numeric not null,
    cash_balance numeric not null,
    buying_power numeric not null,
    sma numeric not null,
    
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,

    -- Ensure one snapshot per portfolio per day for idempotency
    unique(portfolio_id, date)
);

-- Enable RLS
alter table public.portfolio_performance enable row level security;

-- Policies
create policy "Enable read access for all users" on public.portfolio_performance for select using (true);
