-- Create ingestion_logs table for storing pipeline stdout/stderr blobs
CREATE TABLE IF NOT EXISTS public.ingestion_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id TEXT NOT NULL UNIQUE,
    run_date DATE NOT NULL,
    run_number INT NOT NULL,
    log_blob TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_logs_run_date ON public.ingestion_logs(run_date DESC);
CREATE INDEX IF NOT EXISTS idx_ingestion_logs_created_at ON public.ingestion_logs(created_at DESC);

ALTER TABLE public.ingestion_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access for ingestion_logs"
ON public.ingestion_logs
FOR SELECT
TO anon, authenticated
USING (true);

CREATE POLICY "Allow service_role full access for ingestion_logs"
ON public.ingestion_logs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);