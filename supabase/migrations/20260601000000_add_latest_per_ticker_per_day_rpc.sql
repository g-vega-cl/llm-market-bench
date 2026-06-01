-- Migration: Add latest_per_ticker_per_day RPC for homepage hero.
--
-- Why this exists
-- ---------------
-- The homepage hero (`MarketStatusHero`) needs ~45 days of price history
-- for the macro tickers to compute volatility/returns. The current
-- implementation pulls 5000 raw rows from `price_history` and dedupes in
-- JS to keep at most one row per (ticker, date). This wastes network
-- bandwidth (we transfer 5000 rows to throw 4500+ away) and inflates the
-- homepage HTML document by tens of KB.
--
-- This RPC returns the most-recent row per (ticker, date) for the given
-- tickers, server-side. The web app then consumes a pre-deduped payload
-- (~50 rows) and the JS dedup loop in `buildHistoryGroup` is a no-op.

CREATE OR REPLACE FUNCTION latest_per_ticker_per_day(
    p_tickers TEXT[],
    p_days INT DEFAULT 45
)
RETURNS TABLE (
    ticker TEXT,
    price NUMERIC,
    fetched_at TIMESTAMPTZ
) AS $$
DECLARE
    cutoff TIMESTAMPTZ := NOW() - (p_days || ' days')::INTERVAL;
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (ph.ticker, (ph.fetched_at AT TIME ZONE 'America/New_York')::date)
        ph.ticker,
        ph.price,
        ph.fetched_at
    FROM price_history ph
    WHERE ph.ticker = ANY(p_tickers)
      AND ph.fetched_at >= cutoff
    ORDER BY ph.ticker, (ph.fetched_at AT TIME ZONE 'America/New_York')::date DESC, ph.fetched_at DESC;
END;
$$ LANGUAGE plpgsql STABLE;
