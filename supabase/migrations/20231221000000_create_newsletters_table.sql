CREATE TABLE newsletter_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL,
    chunk_hash TEXT NOT NULL,
    sender TEXT NOT NULL,
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(date, source_id)
);

-- Enable RLS
ALTER TABLE newsletter_snapshots ENABLE ROW LEVEL SECURITY;

-- Policy to allow the service role to do everything
CREATE POLICY "Allow service role full access" ON newsletter_snapshots
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
