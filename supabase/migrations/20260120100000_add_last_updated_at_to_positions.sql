-- Add last_updated_at to portfolio_positions for auditing
ALTER TABLE public.portfolio_positions 
ADD COLUMN last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL;
