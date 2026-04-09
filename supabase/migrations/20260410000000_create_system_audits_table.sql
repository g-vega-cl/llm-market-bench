-- Create system_audits table for tracking database anomalies and code issues
CREATE TABLE IF NOT EXISTS public.system_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    suggestion TEXT,
    status TEXT DEFAULT 'OPEN',
    source_table TEXT,
    source_id UUID,
    metadata JSONB DEFAULT '{}',
    audit_run_id TEXT,
    analysis_method TEXT,
    created_by TEXT DEFAULT 'SYSTEM',
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_system_audits_status ON public.system_audits(status);
CREATE INDEX IF NOT EXISTS idx_system_audits_audit_type ON public.system_audits(audit_type);
CREATE INDEX IF NOT EXISTS idx_system_audits_created_at ON public.system_audits(created_at DESC);

ALTER TABLE public.system_audits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access for system_audits"
ON public.system_audits
FOR SELECT
TO anon, authenticated
USING (true);

CREATE POLICY "Allow service_role full access for system_audits"
ON public.system_audits
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);