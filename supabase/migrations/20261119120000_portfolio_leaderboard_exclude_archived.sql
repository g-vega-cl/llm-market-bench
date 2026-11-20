-- ============================================================================
-- Migration: 20261119120000_portfolio_leaderboard_exclude_archived.sql
-- Description:
--   The board ranked portfolios the site had already retired. `models.json`
--   declares ARCHIVED_PORTFOLIO_OWNER_IDS and the engine honours it (archived
--   owners are never marked to market again), but this view — written after that
--   list — never read it, so eight retired system portfolios held ranks 3, 5, 6,
--   7, 17, 19 and 24, and GPT 5.6 Luna appeared twice.
--
--   A retired portfolio is not a competitor: it is a record. It is excluded here,
--   before ranking, so the rank column, the median, the worst row and the count
--   all describe the same population. The series views join this view and inherit
--   the exclusion without a change of their own.
--
--   Two groups are excluded:
--     1. Every owner id declared in packages/config/models.json
--        (ARCHIVED_PORTFOLIO_OWNER_IDS) — the canonical list; the engine test
--        `apps/engine/tests/test_archived_portfolios.py` fails the build when an
--        id is declared there but missing from this array.
--     2. Owners whose model has been replaced in models.json and that have not
--        traded since (gpt-5.6-luna -> gpt-6-luna, MiniMax-M3 ->
--        MiniMax-M3.1-Flash, deepseek-v4-flash -> deepseek-flash). They are not
--        declared archived, so the engine still marks them to market; they are
--        "outdated" rather than retired, and only the board needs to say so.
-- ============================================================================

CREATE OR REPLACE VIEW public.portfolio_leaderboard
WITH (security_invoker = true) AS
WITH excluded(owner_id) AS (
    VALUES
        -- Declared in models.json (ARCHIVED_PORTFOLIO_OWNER_IDS).
        ('sys-daily-spy-MiniMax-M3'),
        ('sys-daily-spy-close-MiniMax-M3'),
        ('sys-daily-spy-deepseek-v4-flash'),
        ('sys-daily-spy-close-deepseek-v4-flash'),
        ('sys-daily-tlt-close-deepseek-v4-flash'),
        ('sys-daily-tlt-close-gpt-5.6-luna'),
        ('sys-daily-spy-close-jev-local-autoresearched'),
        ('sys-daily-spy-close-jev-four-regime-champion'),
        -- Superseded in models.json; no trade since the replacement went live.
        ('gpt-5.6-luna'),
        ('MiniMax-M3'),
        ('deepseek-v4-flash')
),
bounds AS (
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
      -- Retired and superseded owners are records, not competitors.
      AND p.owner_id NOT IN (SELECT owner_id FROM excluded)
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
    'Public homepage ranking: every live portfolio by return from its window-start anchor (30 days, min 5 observations, flat series excluded, archived/superseded owners excluded before ranking). median_return_pct is the median of that population.';
