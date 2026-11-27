-- ============================================================================
-- Migration: 20261127120000_leaderboard_up_days_columns.sql
-- Description:
--   Persist `up_days` / `active_days` next to `consistency_score` on
--   `public.user_bot_leaderboard_stats` and backfill them from the paper equity
--   curves, so the leaderboard can show the raw counts behind a Laplace-smoothed
--   up-day rate (e.g. `9/10 · 78.6%`) instead of a bare percentage that looks
--   like a return-stability or pass-rate metric.
--
--   The backfill intentionally lives in this migration (not the RPC one) so the
--   request-path RPC definitions stay free of `jsonb_array_elements`, which
--   `apps/engine/tests/test_conviction_migration.py` enforces.
-- ============================================================================

ALTER TABLE public.user_bot_leaderboard_stats
    ADD COLUMN IF NOT EXISTS up_days BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS active_days BIGINT NOT NULL DEFAULT 0;

COMMENT ON COLUMN public.user_bot_leaderboard_stats.up_days IS
    'Sessions in the window where closing equity rose (numerator of consistency_score).';
COMMENT ON COLUMN public.user_bot_leaderboard_stats.active_days IS
    'Sessions in the window where closing equity moved (denominator of consistency_score).';

-- One-time backfill from the same daily-collapsed equity curve the materializer
-- reads, so existing rows render counts before the next refresh.
WITH windows(w) AS (
    VALUES (7), (30), (90), (0)
),
bots AS (
    SELECT
        sr.id AS recipe_id,
        CASE WHEN jsonb_typeof(sr.paper_equity_curve) = 'array'
             THEN sr.paper_equity_curve ELSE '[]'::jsonb END AS paper_equity_curve
    FROM public.strategy_recipes sr
    WHERE sr.archived_at IS NULL
      AND sr.is_template = FALSE
      AND sr.is_public = TRUE
      AND sr.user_id <> '00000000-0000-0000-0000-000000000000'
      AND jsonb_typeof(sr.graph_json->'stages') = 'array'
      AND jsonb_array_length(sr.graph_json->'stages') = 1
),
curve_pts AS (
    SELECT
        b.recipe_id,
        pt.ord,
        public._safe_iso_date(pt.elem->>'time') AS pt_date,
        (pt.elem->>'equity')::NUMERIC AS equity
    FROM bots b
    CROSS JOIN LATERAL jsonb_array_elements(b.paper_equity_curve) WITH ORDINALITY AS pt(elem, ord)
    WHERE public._safe_iso_date(pt.elem->>'time') IS NOT NULL
      AND (pt.elem->>'equity') ~ '^-?\d+(\.\d+)?$'
),
daily_close AS (
    SELECT DISTINCT ON (cp.recipe_id, cp.pt_date)
        cp.recipe_id,
        cp.pt_date,
        cp.equity
    FROM curve_pts cp
    ORDER BY cp.recipe_id, cp.pt_date ASC, cp.ord DESC
),
daily_ordered AS (
    SELECT
        dc.recipe_id,
        dc.pt_date,
        dc.equity,
        LAG(dc.equity) OVER (PARTITION BY dc.recipe_id ORDER BY dc.pt_date ASC) AS prev_equity
    FROM daily_close dc
),
session_counts AS (
    SELECT
        d.recipe_id,
        wn.w AS time_window_days,
        COUNT(*) FILTER (WHERE d.equity > d.prev_equity)::BIGINT AS up_days,
        COUNT(*)::BIGINT AS active_days
    FROM daily_ordered d
    CROSS JOIN windows wn
    WHERE d.prev_equity IS NOT NULL
      AND d.prev_equity > 0
      AND d.equity <> d.prev_equity
      AND (wn.w = 0 OR d.pt_date >= (CURRENT_DATE - wn.w))
    GROUP BY d.recipe_id, wn.w
)
UPDATE public.user_bot_leaderboard_stats ubs
SET
    up_days = sc.up_days,
    active_days = sc.active_days
FROM session_counts sc
WHERE sc.recipe_id = ubs.recipe_id
  AND sc.time_window_days = ubs.time_window_days;

NOTIFY pgrst, 'reload schema';
