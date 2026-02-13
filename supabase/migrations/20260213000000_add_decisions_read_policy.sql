-- Migration: Allow read access to decisions table for Steps 7+ analysis
-- Created: 2026-02-13

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'decisions' 
        AND policyname = 'Allow public read access to decisions'
    ) THEN
        CREATE POLICY "Allow public read access to decisions" ON decisions
            FOR SELECT
            USING (true);
    END IF;
END $$;

-- Also ensure authenticated users can read it
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'decisions' 
        AND policyname = 'Allow authenticated read access to decisions'
    ) THEN
        CREATE POLICY "Allow authenticated read access to decisions" ON decisions
            FOR SELECT
            TO authenticated
            USING (true);
    END IF;
END $$;
