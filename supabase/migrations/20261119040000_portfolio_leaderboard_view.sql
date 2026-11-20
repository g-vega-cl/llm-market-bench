-- ============================================================================
-- Migration: 20261119040000_portfolio_leaderboard_view.sql
-- Description:
--   public.portfolio_leaderboard — public read model for the homepage portfolio
--   spotlight and equity chart. Ranking happens in SQL so the web layer stays
--   presentation-only.
--
--   Every row is anchored to the portfolio's equity at the window start (the last
--   snapshot at or before CURRENT_DATE - 30 days), falling back to its first
--   in-window snapshot for portfolios younger than the window. Return and chart
--   share that one anchor, so a series that begins four sessions late is not
--   handed a free 0% head start.
--
--   Mechanical sys-* strategies compete on the same board as the LLM agents: the
--   LLM agent portfolios carried no trades at the time of writing, so excluding
--   sys-* would render an empty hero.
-- ============================================================================

-- Dropped and recreated because the column set changed from the first draft
-- (CREATE OR REPLACE cannot reorder or rename view columns).
DROP VIEW IF EXISTS public.portfolio_leaderboard;

CREATE VIEW public.portfolio_leaderboard
WITH (security_invoker = true) AS
WITH bounds AS (
    SELECT (CURRENT_DATE - INTERVAL '30 days')::date AS window_start
),
windowed AS (
    SELECT
        pp.portfolio_id,
        pp.date,
        pp.total_equity
    FROM public.portfolio_performance pp, bounds b
    WHERE pp.date >= b.window_start
),
anchored AS (
    SELECT
        w.portfolio_id,
        COUNT(*) AS observations,
        MIN(w.date) AS first_date,
        MAX(w.date) AS last_date,
        (array_agg(w.total_equity ORDER BY w.date DESC))[1] AS last_equity,
        COALESCE(prior.date, (array_agg(w.date ORDER BY w.date ASC))[1]) AS anchor_date,
        COALESCE(prior.total_equity, (array_agg(w.total_equity ORDER BY w.date ASC))[1])
            AS anchor_equity
    FROM windowed w
    LEFT JOIN LATERAL (
        SELECT p2.date, p2.total_equity
        FROM public.portfolio_performance p2, bounds b
        WHERE p2.portfolio_id = w.portfolio_id
          AND p2.date < b.window_start
        ORDER BY p2.date DESC
        LIMIT 1
    ) prior ON true
    GROUP BY w.portfolio_id, prior.date, prior.total_equity
),
ranked AS (
    SELECT
        a.portfolio_id,
        p.owner_id,
        a.first_date,
        a.last_date,
        a.observations,
        a.anchor_date,
        a.anchor_equity,
        a.last_equity,
        ROUND(((a.last_equity / NULLIF(a.anchor_equity, 0)) - 1) * 100, 4) AS return_pct,
        RANK() OVER (
            ORDER BY (a.last_equity / NULLIF(a.anchor_equity, 0)) DESC, a.portfolio_id
        ) AS rank
    FROM anchored a
    JOIN public.portfolios p ON p.id = a.portfolio_id
    WHERE a.observations >= 5
      AND a.anchor_equity > 0
      AND a.last_equity <> a.anchor_equity
      -- A portfolio that stopped reporting cannot hold a rank: the board's newest
      -- observation is the reference, and three sessions of slack covers a gap.
      AND a.last_date >= (SELECT MAX(date) FROM public.portfolio_performance) - 3
)
SELECT
    r.*,
    (SELECT window_start FROM bounds) AS window_start,
    30::int AS window_days,
    (
        SELECT ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY m.return_pct))::numeric, 4)
        FROM ranked m
    ) AS median_return_pct
FROM ranked r;

COMMENT ON VIEW public.portfolio_leaderboard IS
    'Public homepage ranking: every tracked portfolio by return from its window-start anchor (30 days, min 5 observations, flat series excluded). median_return_pct is the median of that population.';

-- The homepage reads this through the service-role server fn; security_invoker
-- keeps base-table RLS in force if the read role ever stops bypassing it.
GRANT SELECT ON public.portfolio_leaderboard TO service_role;
REVOKE ALL ON public.portfolio_leaderboard FROM anon, authenticated;
