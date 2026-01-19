-- Add status and metadata to decisions for rejection layer
ALTER TABLE decisions 
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'CREATED',
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Optional: Update enum check constraint if signal constraint exists
-- Since signal is just text, we don't need to change it, 
-- but we might want status to be an enum later.
