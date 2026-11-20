-- ============================================================================
-- Migration: 20261119060000_portfolio_leaderboard_series_views.sql
-- Description:
--   Moves the last percentage arithmetic out of the web layer. The homepage
--   loader used to fetch raw total_equity rows and rebase them in TypeScript,
--   which is a (small) violation of the presentation-only mandate and the same
--   habit that let the chart and the ranking drift onto different anchors.
--
--   portfolio_leaderboard_series — one row per portfolio-day, already expressed
--   as percent return from that portfolio's ranking anchor.
--   spy_benchmark_series — the same for SPY, anchored at the earliest anchor date
--   the board used, one row per session (last price of the day wins).
-- ============================================================================

CREATE OR REPLACE VIEW public.portfolio_leaderboard_series
WITH (security_invoker = true) AS
SELECT
    pp.portfolio_id,
    pp.date,
    ROUND(((pp.total_equity / NULLIF(l.anchor_equity, 0)) - 1) * 100, 4) AS return_pct
FROM public.portfolio_performance pp
JOIN public.portfolio_leaderboard l ON l.portfolio_id = pp.portfolio_id
WHERE pp.date >= l.anchor_date;

COMMENT ON VIEW public.portfolio_leaderboard_series IS
    'Homepage chart series: each portfolio-day as percent return from that portfolio''s ranking anchor.';

CREATE OR REPLACE VIEW public.spy_benchmark_series
WITH (security_invoker = true) AS
WITH anchor AS (
    SELECT COALESCE(MIN(anchor_date), CURRENT_DATE - INTERVAL '30 days') AS from_date
    FROM public.portfolio_leaderboard
),
daily AS (
    SELECT DISTINCT ON (date_trunc('day', ph.fetched_at)::date)
        date_trunc('day', ph.fetched_at)::date AS date,
        ph.price
    FROM public.price_history ph, anchor
    WHERE ph.ticker = 'SPY'
      AND ph.fetched_at >= anchor.from_date
    ORDER BY date_trunc('day', ph.fetched_at)::date, ph.fetched_at DESC
)
SELECT
    date,
    price,
    ROUND((price / first_value(price) OVER (ORDER BY date) - 1) * 100, 4) AS return_pct
FROM daily;

COMMENT ON VIEW public.spy_benchmark_series IS
    'Homepage benchmark: SPY one row per session, percent return from the board''s earliest anchor.';

GRANT SELECT ON public.portfolio_leaderboard_series TO service_role;
GRANT SELECT ON public.spy_benchmark_series TO service_role;
REVOKE ALL ON public.portfolio_leaderboard_series FROM anon, authenticated;
REVOKE ALL ON public.spy_benchmark_series FROM anon, authenticated;
