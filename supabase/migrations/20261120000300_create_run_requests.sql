-- "Ask for more runs": one row per user per ET day, so a double submit is a
-- 23505 the UI can explain instead of a duplicate. The date column is a stored
-- value, not an expression: `UNIQUE (date_trunc(...))` is not valid DDL.

CREATE TABLE IF NOT EXISTS public.run_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '' CHECK (char_length(note) <= 280),
    request_day DATE NOT NULL DEFAULT ((NOW() AT TIME ZONE 'America/New_York')::DATE),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done', 'declined')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, request_day)
);

ALTER TABLE public.run_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role manages run requests" ON public.run_requests;
CREATE POLICY "Service role manages run requests"
    ON public.run_requests FOR ALL TO service_role USING (true) WITH CHECK (true);

REVOKE ALL ON public.run_requests FROM anon, authenticated;
GRANT ALL ON public.run_requests TO service_role;

CREATE INDEX IF NOT EXISTS idx_run_requests_created
    ON public.run_requests (created_at DESC);

NOTIFY pgrst, 'reload schema';
