-- Update owner_id for the MiniMax portfolio
UPDATE public.portfolios
SET owner_id = 'MiniMax-M3'
WHERE owner_id = 'MiniMax-M2.7';

-- Update model_used default value in market_feeling table
ALTER TABLE public.market_feeling
ALTER COLUMN model_used SET DEFAULT 'MiniMax-M3';

-- Update historical market feeling records
UPDATE public.market_feeling
SET model_used = 'MiniMax-M3'
WHERE model_used = 'MiniMax-M2.7';
