-- Migration: Allow public read access to newsletter_snapshots
-- Rationale: Allows the web application (using the anon key) to display daily intelligence briefings on the Today page.
-- Created: 2026-06-24

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'newsletter_snapshots' 
        AND policyname = 'Allow public read access to newsletter_snapshots'
    ) THEN
        CREATE POLICY "Allow public read access to newsletter_snapshots" ON newsletter_snapshots
            FOR SELECT
            USING (true);
    END IF;
END $$;

-- Ensure authenticated users can also read it
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'newsletter_snapshots' 
        AND policyname = 'Allow authenticated read access to newsletter_snapshots'
    ) THEN
        CREATE POLICY "Allow authenticated read access to newsletter_snapshots" ON newsletter_snapshots
            FOR SELECT
            TO authenticated
            USING (true);
    END IF;
END $$;

-- REQUIRED: Explicit grants for Data API access (anon, authenticated)
GRANT SELECT ON public.newsletter_snapshots TO anon, authenticated;
