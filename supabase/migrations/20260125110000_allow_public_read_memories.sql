-- Allow public read access to memories
-- This allows the public page to show the gathered memories without authentication
CREATE POLICY "Allow public read access to memories" ON memories
    FOR SELECT
    USING (true);
