-- Create trade_rejections table for detailed auditing of failed execution
CREATE TABLE IF NOT EXISTS public.trade_rejections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    ticker TEXT NOT NULL,
    requested_action TEXT NOT NULL, -- BUY or SELL
    requested_quantity INTEGER,
    market_price NUMERIC,
    cash_before NUMERIC,
    cash_after NUMERIC,
    position_before INTEGER,
    rejection_reason TEXT NOT NULL,
    decision_trace_id UUID REFERENCES decisions(id),
    tool_trace_id UUID, -- Links to llm_reasoning_logs
    portfolio_id UUID REFERENCES portfolios(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for auditing
CREATE INDEX idx_trade_rejections_ticker ON public.trade_rejections(ticker);
CREATE INDEX idx_trade_rejections_provider ON public.trade_rejections(provider);
CREATE INDEX idx_trade_rejections_created_at ON public.trade_rejections(created_at);

-- Add normalized_transcript column to reasoning logs for efficient querying
ALTER TABLE public.llm_reasoning_logs
ADD COLUMN IF NOT EXISTS normalized_transcript JSONB;

-- Enable RLS
ALTER TABLE public.trade_rejections ENABLE ROW LEVEL SECURITY;

-- Allow service role access
CREATE POLICY "Service role full access on trade_rejections" ON public.trade_rejections
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Allow public read for audit visibility
CREATE POLICY "Public read on trade_rejections" ON public.trade_rejections
    FOR SELECT USING (true);
