-- Migration: Enable Row Level Security and access policies on options_data_cache
-- Resolves Supabase Security Advisor vulnerability: rls_disabled_in_public

-- 1. Enable Row-Level Security
ALTER TABLE public.options_data_cache ENABLE ROW LEVEL SECURITY;

-- 2. Create access policies idempotently
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'options_data_cache'
          AND policyname = 'Allow public read access to options_data_cache'
    ) THEN
        CREATE POLICY "Allow public read access to options_data_cache"
            ON public.options_data_cache FOR SELECT
            TO anon, authenticated, service_role
            USING (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'options_data_cache'
          AND policyname = 'Allow service role full access to options_data_cache'
    ) THEN
        CREATE POLICY "Allow service role full access to options_data_cache"
            ON public.options_data_cache FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;

-- 3. Explicit Data API grants
GRANT SELECT ON public.options_data_cache TO anon, authenticated;
GRANT ALL ON public.options_data_cache TO service_role;
