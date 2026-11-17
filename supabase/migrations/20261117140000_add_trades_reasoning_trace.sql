-- Preserve the live intraday trader's full chain of thought per fill.
-- `trades.reasoning` keeps the short 2-3 sentence `thought` that the UI renders;
-- `reasoning_trace` stores the model's raw thinking (free-llm-proxy
-- `message.reasoning`) so post-mortems can audit why a decision was made instead
-- of only the summarized rationale. Nullable: every other portfolio and all
-- historical rows simply have no captured trace.

ALTER TABLE public.trades ADD COLUMN IF NOT EXISTS reasoning_trace TEXT;

COMMENT ON COLUMN public.trades.reasoning_trace IS
    'Full model chain-of-thought captured for the decision that produced this trade (live-spy-trader). NULL when the model or portfolio supplies no reasoning.';
