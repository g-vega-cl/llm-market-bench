-- ============================================================================
-- Migration: 20261125010000_create_user_bot_leaderboard_stats.sql
-- Description:
--   1. Create `public.user_bot_leaderboard_stats` to store pre-materialized
--      per-window (7d, 30d, 90d, 0=All-Time) metrics for public user bots so
--      `/leaderboard` never unpacks `strategy_recipes.paper_*` JSONB on reads.
--   2. Add RLS policies and explicit GRANTs per repo security conventions.
--   3. One-time backfill of existing public non-archived single-stage user bots.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.user_bot_leaderboard_stats (
    recipe_id UUID NOT NULL REFERENCES public.strategy_recipes(id) ON DELETE CASCADE,
    time_window_days INTEGER NOT NULL CHECK (time_window_days IN (0, 7, 30, 90)),
    total_equity NUMERIC(14, 2) NOT NULL DEFAULT 10000.00,
    return_pct NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    realized_pnl NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    win_rate NUMERIC(6, 2),
    total_trades BIGINT NOT NULL DEFAULT 0,
    consistency_score NUMERIC(6, 2) NOT NULL DEFAULT 50.00,
    trading_activity_rate NUMERIC(6, 2) NOT NULL DEFAULT 0.00,
    has_activity BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (recipe_id, time_window_days)
);

CREATE INDEX IF NOT EXISTS idx_user_bot_lb_stats_window
    ON public.user_bot_leaderboard_stats (time_window_days, recipe_id);

ALTER TABLE public.user_bot_leaderboard_stats ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read on user_bot_leaderboard_stats" ON public.user_bot_leaderboard_stats;
CREATE POLICY "Allow public read on user_bot_leaderboard_stats"
    ON public.user_bot_leaderboard_stats
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Allow service_role full access on user_bot_leaderboard_stats" ON public.user_bot_leaderboard_stats;
CREATE POLICY "Allow service_role full access on user_bot_leaderboard_stats"
    ON public.user_bot_leaderboard_stats
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

GRANT SELECT ON public.user_bot_leaderboard_stats TO anon, authenticated;
GRANT ALL ON public.user_bot_leaderboard_stats TO service_role;

COMMENT ON TABLE public.user_bot_leaderboard_stats IS
    'Runner-materialised per-window leaderboard metrics for public user bots (7d, 30d, 90d, 0=All-Time).';

-- One-time backfill for all existing public, non-archived, single-stage user bots
INSERT INTO public.user_bot_leaderboard_stats (
    recipe_id,
    time_window_days,
    total_equity,
    return_pct,
    realized_pnl,
    win_rate,
    total_trades,
    consistency_score,
    trading_activity_rate,
    has_activity,
    updated_at
)
WITH windows(w) AS (
    VALUES (7), (30), (90), (0)
),
bots AS (
    SELECT
        sr.id AS recipe_id,
        COALESCE(sr.paper_cash, 10000.0)::NUMERIC AS paper_cash,
        CASE WHEN jsonb_typeof(sr.paper_positions) = 'array' THEN sr.paper_positions ELSE '[]'::jsonb END AS paper_positions,
        CASE WHEN jsonb_typeof(sr.paper_trades) = 'array' THEN sr.paper_trades ELSE '[]'::jsonb END AS paper_trades,
        CASE WHEN jsonb_typeof(sr.paper_equity_curve) = 'array' THEN sr.paper_equity_curve ELSE '[]'::jsonb END AS paper_equity_curve
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
pos_summary AS (
    SELECT
        b.recipe_id,
        COALESCE(SUM(
            CASE
                WHEN (pos.elem->>'market_value') ~ '^-?\d+(\.\d+)?$'
                    THEN (pos.elem->>'market_value')::NUMERIC
                WHEN (pos.elem->>'shares') ~ '^-?\d+(\.\d+)?$'
                 AND COALESCE(NULLIF(pos.elem->>'current_price', ''), NULLIF(pos.elem->>'entry_price', '')) ~ '^-?\d+(\.\d+)?$'
                    THEN (pos.elem->>'shares')::NUMERIC * COALESCE(NULLIF(pos.elem->>'current_price', ''), NULLIF(pos.elem->>'entry_price', ''))::NUMERIC
                ELSE 0.0
            END
        ), 0.0) AS positions_value,
        COUNT(CASE
            WHEN (
                CASE
                    WHEN (pos.elem->>'unrealized_pnl_net') ~ '^-?\d+(\.\d+)?$'
                        THEN (pos.elem->>'unrealized_pnl_net')::NUMERIC
                    WHEN (pos.elem->>'shares') ~ '^-?\d+(\.\d+)?$'
                     AND (pos.elem->>'current_price') ~ '^-?\d+(\.\d+)?$'
                     AND (pos.elem->>'entry_price') ~ '^-?\d+(\.\d+)?$'
                        THEN ((pos.elem->>'current_price')::NUMERIC - (pos.elem->>'entry_price')::NUMERIC) * (pos.elem->>'shares')::NUMERIC
                    ELSE 0.0
                END
            ) > 0 THEN 1
        END)::BIGINT AS open_wins,
        COUNT(*)::BIGINT AS open_total
    FROM bots b
    CROSS JOIN LATERAL jsonb_array_elements(b.paper_positions) AS pos(elem)
    GROUP BY b.recipe_id
),
windowed AS (
    SELECT
        b.recipe_id,
        w.w AS time_window_days,
        CASE WHEN w.w > 0 THEN (CURRENT_DATE - (w.w || ' days')::INTERVAL)::DATE ELSE NULL::DATE END AS start_date,
        GREATEST(1, CASE WHEN w.w > 0 THEN (w.w * 5 / 7) ELSE 20 END)::NUMERIC AS est_weekdays,
        COALESCE(
            (SELECT cp.equity FROM curve_pts cp WHERE cp.recipe_id = b.recipe_id ORDER BY cp.pt_date DESC, cp.ord DESC LIMIT 1),
            b.paper_cash + COALESCE(ps.positions_value, 0.0),
            10000.00
        ) AS last_eq,
        COALESCE(
            (SELECT dc.equity FROM daily_close dc
             WHERE dc.recipe_id = b.recipe_id
               AND dc.pt_date <= COALESCE(CASE WHEN w.w > 0 THEN (CURRENT_DATE - (w.w || ' days')::INTERVAL)::DATE ELSE '1900-01-01'::DATE END, '1900-01-01'::DATE)
             ORDER BY dc.pt_date DESC LIMIT 1),
            10000.00
        ) AS start_eq,
        COALESCE(ps.open_wins, 0)::BIGINT AS open_wins,
        COALESCE(ps.open_total, 0)::BIGINT AS open_total,
        b.paper_trades
    FROM bots b
    CROSS JOIN windows w
    LEFT JOIN pos_summary ps ON ps.recipe_id = b.recipe_id
),
windowed_trades AS (
    SELECT
        wn.recipe_id,
        wn.time_window_days,
        COALESCE(SUM((tr.elem->>'pnl_net')::NUMERIC), 0.0) AS sum_realized_pnl,
        COUNT(CASE WHEN (tr.elem->>'pnl_net')::NUMERIC > 0 THEN 1 END)::BIGINT AS closed_wins,
        COUNT(*)::BIGINT AS closed_total
    FROM windowed wn
    CROSS JOIN LATERAL jsonb_array_elements(wn.paper_trades) AS tr(elem)
    WHERE (tr.elem->>'pnl_net') ~ '^-?\d+(\.\d+)?$'
      AND (
          wn.start_date IS NULL
          OR public._safe_iso_date(COALESCE(NULLIF(tr.elem->>'exit_time', ''), NULLIF(tr.elem->>'entry_time', ''))) >= wn.start_date
      )
    GROUP BY wn.recipe_id, wn.time_window_days
),
windowed_cons AS (
    SELECT
        wn.recipe_id,
        wn.time_window_days,
        COUNT(CASE WHEN d.equity > d.prev_equity THEN 1 END)::BIGINT AS pos_days,
        COUNT(*)::BIGINT AS active_return_days
    FROM windowed wn
    JOIN daily_ordered d ON d.recipe_id = wn.recipe_id
    WHERE (wn.start_date IS NULL OR d.pt_date >= wn.start_date)
      AND d.prev_equity IS NOT NULL
      AND d.prev_equity > 0
      AND d.equity <> d.prev_equity
    GROUP BY wn.recipe_id, wn.time_window_days
)
SELECT
    wn.recipe_id,
    wn.time_window_days,
    ROUND(wn.last_eq, 2) AS total_equity,
    ROUND(COALESCE(((wn.last_eq - wn.start_eq) / NULLIF(wn.start_eq, 0)) * 100.0, 0.0), 2) AS return_pct,
    ROUND(COALESCE(wt.sum_realized_pnl, 0.0), 2) AS realized_pnl,
    CASE
        WHEN (COALESCE(wt.closed_total, 0) + wn.open_total) > 0 THEN
            ROUND(((COALESCE(wt.closed_wins, 0) + wn.open_wins)::NUMERIC * 100.0) / (COALESCE(wt.closed_total, 0) + wn.open_total), 2)
        ELSE NULL::NUMERIC
    END AS win_rate,
    COALESCE(wt.closed_total, 0::BIGINT) AS total_trades,
    ROUND(((COALESCE(wc.pos_days, 0)::NUMERIC + 2.0) * 100.0) / (COALESCE(wc.active_return_days, 0)::NUMERIC + 4.0), 2) AS consistency_score,
    ROUND(LEAST(COALESCE((COALESCE(wc.active_return_days, 0)::NUMERIC / wn.est_weekdays) * 100.0, 0.0), 100.0), 2) AS trading_activity_rate,
    (
        COALESCE(wt.closed_total, 0) > 0
        OR wn.open_total > 0
        OR COALESCE(wc.active_return_days, 0) > 0
        OR ABS(wn.last_eq - wn.start_eq) > 0.01
    ) AS has_activity,
    NOW() AS updated_at
FROM windowed wn
LEFT JOIN windowed_trades wt ON wt.recipe_id = wn.recipe_id AND wt.time_window_days = wn.time_window_days
LEFT JOIN windowed_cons wc ON wc.recipe_id = wn.recipe_id AND wc.time_window_days = wn.time_window_days
ON CONFLICT (recipe_id, time_window_days) DO UPDATE SET
    total_equity = EXCLUDED.total_equity,
    return_pct = EXCLUDED.return_pct,
    realized_pnl = EXCLUDED.realized_pnl,
    win_rate = EXCLUDED.win_rate,
    total_trades = EXCLUDED.total_trades,
    consistency_score = EXCLUDED.consistency_score,
    trading_activity_rate = EXCLUDED.trading_activity_rate,
    has_activity = EXCLUDED.has_activity,
    updated_at = EXCLUDED.updated_at;

NOTIFY pgrst, 'reload schema';
