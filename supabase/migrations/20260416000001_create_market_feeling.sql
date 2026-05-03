-- Create market_feeling table for LLM-driven market sentiment
-- This table stores the AI's "How I'm feeling and why" analysis
-- Refreshed multiple times daily during market hours

CREATE TABLE market_feeling (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Core sentiment (LLM-generated)
    sentiment_label TEXT NOT NULL,
    sentiment_emoji TEXT,
    confidence_score INTEGER,

    -- Structured output from LLM
    why_explanation TEXT,
    market_direction TEXT CHECK (market_direction IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
    primary_concern TEXT,
    secondary_concern TEXT,

    -- Supporting context (for audit trail)
    trades_summary JSONB,
    lessons_incorporated INTEGER,
    memories_incorporated INTEGER,

    -- Metadata
    model_used TEXT DEFAULT 'MiniMax-M2.7',
    processing_time_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER
);

-- Index for fast lookups (most recent first)
CREATE INDEX idx_market_feeling_created_at ON market_feeling(created_at DESC);

-- RLS policies
ALTER TABLE market_feeling ENABLE ROW LEVEL SECURITY;

-- Public can read (like memories table)
CREATE POLICY "Public can read market_feeling" ON market_feeling
    FOR SELECT USING (true);

-- Service role can write (engine uses service_role key)
CREATE POLICY "Service role can write market_feeling" ON market_feeling
    FOR ALL USING (auth.role() = 'service_role');

-- Cleanup job: Delete records older than 30 days
-- This runs automatically to manage table size
CREATE OR REPLACE FUNCTION cleanup_old_market_feelings()
RETURNS void AS $$
BEGIN
    DELETE FROM market_feeling WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Note: For automated cleanup, consider adding this to a cron job or GitHub Actions
-- Example: psql $DATABASE_URL -c "SELECT cleanup_old_market_feelings();"

COMMENT ON TABLE market_feeling IS 'LLM-generated market sentiment (How I''m feeling and why). Refreshed 3x daily during pipeline runs.';
COMMENT ON COLUMN market_feeling.sentiment_label IS 'E.g., Cautiously Optimistic, Risk-Off, Wait-and-See, Defensive, Opportunistic';
COMMENT ON COLUMN market_feeling.market_direction IS 'BULLISH, BEARISH, or NEUTRAL based on analysis';
COMMENT ON COLUMN market_feeling.why_explanation IS '2-3 sentence explanation of the sentiment';
COMMENT ON COLUMN market_feeling.primary_concern IS 'Main risk or opportunity currently';
COMMENT ON COLUMN market_feeling.secondary_concern IS 'Secondary consideration';