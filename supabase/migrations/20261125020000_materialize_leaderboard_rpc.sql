-- ============================================================================
-- Migration: 20261125020000_materialize_leaderboard_rpc.sql
-- Description:
--   1. Add missing `decisions` indexes (`created_at DESC`, `(model_name, created_at DESC)`).
--   2. Update `get_llm_leaderboard_metrics(time_window_days INT)` (STABLE) to:
--      - Read pre-materialized `public.user_bot_leaderboard_stats` instead of
--        unpacking `strategy_recipes.paper_*` JSONB on request paths.
--      - Enforce the active LLM allowlist + ARCHIVED_PORTFOLIO_OWNER_IDS in SQL.
--      - Include open SHORT lots (`signal = 'SHORT' AND realized_pnl IS NULL`)
--        in `portfolio_open_positions` alongside `position_pnl` LONGs.
--      - Align `total_trades` to closed round-trip exits (`closed_total`).
--      - Return NULL `conviction_score` / `average_confidence` for non-LLMs
--        (`system`, `user_bot`) and weight their composite score over applicable
--        axes (`0.7 * trading_performance + 0.3 * consistency`).
--   3. Add `get_leaderboard_page(...)` (STABLE, GET-routable) for server-side
--      category filtering, sorting, 10-row pagination, counts, and Top 3 podium.
-- ============================================================================

-- 1. Decisions indexes -------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_decisions_created_at
    ON public.decisions (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_decisions_model_created
    ON public.decisions (model_name, created_at DESC);

-- 2. Unified STABLE leaderboard metrics RPC (zero JSONB unpacking) -----------
DROP FUNCTION IF EXISTS public.get_llm_leaderboard_metrics(INT);

CREATE OR REPLACE FUNCTION public.get_llm_leaderboard_metrics(time_window_days INT)
RETURNS TABLE (
    model_name TEXT,
    display_name TEXT,
    entity_type TEXT,
    portfolio_id UUID,
    recipe_id UUID,
    is_live BOOLEAN,
    total_equity NUMERIC,
    return_pct NUMERIC,
    realized_pnl NUMERIC,
    win_rate NUMERIC,
    total_trades BIGINT,
    average_confidence NUMERIC,
    conviction_score NUMERIC,
    api_success_rate NUMERIC,
    trading_activity_rate NUMERIC,
    trading_performance_score NUMERIC,
    reasoning_quality_score NUMERIC,
    consistency_score NUMERIC,
    composite_score NUMERIC
) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
DECLARE
    start_date DATE;
    end_date DATE := CURRENT_DATE;
    total_weekdays INT;
    v_window_key INT := COALESCE(time_window_days, 0);
BEGIN
    IF v_window_key NOT IN (0, 7, 30, 90) THEN
        v_window_key := 30;
    END IF;

    IF time_window_days IS NOT NULL AND time_window_days > 0 THEN
        start_date := (NOW() - (time_window_days || ' days')::INTERVAL)::DATE;
    ELSE
        SELECT LEAST(
            COALESCE((SELECT MIN(created_at)::DATE FROM public.decisions), CURRENT_DATE),
            COALESCE((SELECT MIN(date) FROM public.portfolio_performance), CURRENT_DATE)
        )
        INTO start_date;
    END IF;

    SELECT COUNT(*)::INT INTO total_weekdays
    FROM generate_series(start_date, end_date, '1 day'::interval) d
    WHERE EXTRACT(isodow FROM d) < 6;

    IF total_weekdays <= 0 THEN
        total_weekdays := 1;
    END IF;

    RETURN QUERY
    WITH active_llm_owners(owner_id) AS (
        VALUES
            ('gpt-6-luna'),
            ('claude-haiku-5-5'),
            ('gemini-3.5-flash-lite'),
            ('deepseek-flash'),
            ('MiniMax-M3.1-Flash')
    ),
    archived_owners(owner_id) AS (
        VALUES
            ('sys-daily-spy-MiniMax-M3'),
            ('sys-daily-spy-close-MiniMax-M3'),
            ('sys-daily-spy-deepseek-v4-flash'),
            ('sys-daily-spy-close-deepseek-v4-flash'),
            ('sys-daily-tlt-close-deepseek-v4-flash'),
            ('sys-daily-tlt-close-gpt-5.6-luna'),
            ('sys-daily-spy-close-jev-local-autoresearched'),
            ('sys-daily-spy-close-jev-four-regime-champion'),
            ('gpt-5.6-luna'),
            ('MiniMax-M3'),
            ('deepseek-v4-flash'),
            ('claude-haiku-4-5')
    ),
    active_portfolios AS (
        SELECT
            p.id,
            p.owner_id,
            p.total_equity,
            CASE
                WHEN LOWER(p.owner_id) LIKE 'sys-%' OR LOWER(p.owner_id) LIKE 'sys\_%' ESCAPE '\' THEN 'system'
                ELSE 'llm'
            END AS p_entity_type
        FROM public.portfolios p
        WHERE (
            p.owner_id IN (SELECT owner_id FROM active_llm_owners)
            OR LOWER(p.owner_id) LIKE 'sys-%'
            OR LOWER(p.owner_id) LIKE 'sys\_%' ESCAPE '\'
        )
          AND p.owner_id NOT IN (SELECT owner_id FROM archived_owners)
    ),
    model_decisions AS (
        SELECT
            d.model_name AS m_name,
            COALESCE(AVG(d.confidence), 0.0) AS avg_conf,
            COALESCE(
                (COUNT(CASE WHEN d.status != 'ERROR_PROVIDER' THEN 1 END)::NUMERIC * 100.0) /
                NULLIF(COUNT(d.id), 0),
                0.0
            ) AS api_succ_rate,
            COUNT(DISTINCT (d.created_at::DATE))::INT AS active_days
        FROM public.decisions d
        WHERE d.created_at >= start_date
          AND d.model_name IN (SELECT owner_id FROM active_llm_owners)
        GROUP BY d.model_name
    ),
    model_conviction AS (
        SELECT
            mc.m_name,
            mc.n_predictions,
            ROUND((50.0 + 50.0 * TANH(mc.mean_cp / 50.0))::NUMERIC, 2) AS conviction_norm
        FROM (
            SELECT
                dp.model_name AS m_name,
                COUNT(*)::INT AS n_predictions,
                COALESCE(
                    AVG(
                        CASE
                            WHEN dp.predicted_direction = 'HOLD' THEN 0.0
                            WHEN dp.is_correct IS TRUE
                                THEN 100.0 * LN(2.0 * (0.50 + 0.35 * (GREATEST(LEAST(dp.confidence, 100.0), 50.0) - 50.0) / 50.0))
                            WHEN dp.is_correct IS FALSE
                                THEN 100.0 * LN(2.0 - 2.0 * (0.50 + 0.35 * (GREATEST(LEAST(dp.confidence, 100.0), 50.0) - 50.0) / 50.0))
                            ELSE 0.0
                        END
                    ),
                    0.0
                ) AS mean_cp
            FROM public.daily_predictions dp
            WHERE dp.status = 'evaluated'
              AND dp.target_date >= start_date
              AND dp.model_name IN (SELECT owner_id FROM active_llm_owners)
            GROUP BY dp.model_name
        ) mc
    ),
    portfolio_trades AS (
        SELECT
            ap.id AS portfolio_id,
            COALESCE(
                SUM(
                    CASE
                        WHEN t.signal IN ('SELL', 'COVER') AND t.realized_pnl IS NOT NULL
                            THEN t.realized_pnl
                        ELSE 0.0
                    END
                ),
                0.0
            ) AS sum_realized_pnl,
            COUNT(
                CASE
                    WHEN t.signal IN ('SELL', 'COVER')
                     AND t.realized_pnl IS NOT NULL
                     AND t.realized_pnl > 0
                        THEN 1
                END
            )::BIGINT AS closed_wins,
            COUNT(
                CASE
                    WHEN t.signal IN ('SELL', 'COVER')
                     AND t.realized_pnl IS NOT NULL
                        THEN 1
                END
            )::BIGINT AS closed_total
        FROM active_portfolios ap
        LEFT JOIN public.trades t
            ON t.portfolio_id = ap.id
           AND t.executed_at >= start_date
        GROUP BY ap.id
    ),
    open_short_lots AS (
        SELECT
            t.portfolio_id,
            UPPER(t.ticker) AS ticker,
            t.price AS entry_price,
            COALESCE(mc.price, t.price) AS current_price
        FROM public.trades t
        JOIN active_portfolios ap ON ap.id = t.portfolio_id
        LEFT JOIN public.market_data_cache mc ON UPPER(mc.ticker) = UPPER(t.ticker)
        WHERE UPPER(t.signal) = 'SHORT'
          AND t.realized_pnl IS NULL
          AND NOT EXISTS (
              SELECT 1
              FROM public.trades c
              WHERE c.portfolio_id = t.portfolio_id
                AND UPPER(c.ticker) = UPPER(t.ticker)
                AND UPPER(c.signal) = 'COVER'
                AND c.executed_at >= t.executed_at
          )
    ),
    portfolio_open_positions AS (
        SELECT
            combined_pos.portfolio_id,
            COUNT(CASE WHEN combined_pos.is_win THEN 1 END)::BIGINT AS open_wins,
            COUNT(*)::BIGINT AS open_total
        FROM (
            SELECT
                pp.portfolio_id,
                (pp.unrealized_pnl_usd > 0) AS is_win
            FROM public.position_pnl pp
            UNION ALL
            SELECT
                osl.portfolio_id,
                ((osl.entry_price - osl.current_price) > 0) AS is_win
            FROM open_short_lots osl
        ) combined_pos
        GROUP BY combined_pos.portfolio_id
    ),
    starting_equities AS (
        SELECT
            ap.id AS portfolio_id,
            COALESCE(
                (SELECT pe.total_equity
                 FROM public.portfolio_performance pe
                 WHERE pe.portfolio_id = ap.id AND pe.date <= start_date
                 ORDER BY pe.date DESC
                 LIMIT 1),
                10000.00
            ) AS start_eq
        FROM active_portfolios ap
    ),
    portfolio_perf_ordered AS (
        SELECT
            pe.portfolio_id,
            pe.date,
            pe.total_equity,
            LAG(pe.total_equity) OVER (PARTITION BY pe.portfolio_id ORDER BY pe.date ASC) AS prev_equity
        FROM public.portfolio_performance pe
        JOIN active_portfolios ap ON ap.id = pe.portfolio_id
        WHERE pe.date >= (start_date - INTERVAL '14 days')::DATE
    ),
    portfolio_consistency AS (
        SELECT
            ppo.portfolio_id,
            COUNT(CASE WHEN ppo.total_equity > ppo.prev_equity THEN 1 END)::BIGINT AS pos_days,
            COUNT(*)::BIGINT AS active_return_days
        FROM portfolio_perf_ordered ppo
        WHERE ppo.date >= start_date
          AND ppo.prev_equity IS NOT NULL
          AND ppo.prev_equity > 0
          AND ppo.total_equity <> ppo.prev_equity
        GROUP BY ppo.portfolio_id
    ),
    portfolio_metrics AS (
        SELECT
            ap.owner_id AS model_name,
            ap.owner_id AS display_name,
            ap.p_entity_type AS entity_type,
            ap.id AS portfolio_id,
            NULL::UUID AS recipe_id,
            TRUE AS is_live,
            ap.total_equity,
            ROUND(COALESCE(((ap.total_equity - seq.start_eq) / NULLIF(seq.start_eq, 0)) * 100.0, 0.0), 2) AS return_pct,
            ROUND(COALESCE(pt.sum_realized_pnl, 0.0), 2) AS realized_pnl,
            CASE
                WHEN (COALESCE(pt.closed_total, 0) + COALESCE(pop.open_total, 0)) > 0 THEN
                    ROUND(
                        ((COALESCE(pt.closed_wins, 0) + COALESCE(pop.open_wins, 0))::NUMERIC * 100.0) /
                        (COALESCE(pt.closed_total, 0) + COALESCE(pop.open_total, 0)),
                        2
                    )
                ELSE NULL::NUMERIC
            END AS win_rate,
            COALESCE(pt.closed_total, 0::BIGINT) AS total_trades,
            CASE
                WHEN ap.p_entity_type = 'llm' THEN ROUND(COALESCE(mdec.avg_conf, 0.0), 2)
                ELSE NULL::NUMERIC
            END AS average_confidence,
            CASE
                WHEN ap.p_entity_type = 'llm' THEN ROUND(COALESCE(mconv.conviction_norm, 50.0)::NUMERIC, 2)
                ELSE NULL::NUMERIC
            END AS conviction_score,
            ROUND(COALESCE(mdec.api_succ_rate, 100.0), 2) AS api_success_rate,
            ROUND(
                LEAST(
                    COALESCE((COALESCE(pc.active_return_days, mdec.active_days, 0)::NUMERIC / total_weekdays) * 100.0, 0.0),
                    100.0
                ),
                2
            ) AS trading_activity_rate,
            CASE
                WHEN (COALESCE(pt.closed_total, 0) + COALESCE(pop.open_total, 0)) > 0 THEN
                    ((COALESCE(pt.closed_wins, 0) + COALESCE(pop.open_wins, 0))::NUMERIC * 100.0) /
                    (COALESCE(pt.closed_total, 0) + COALESCE(pop.open_total, 0))
                ELSE 50.0
            END AS effective_win_rate,
            ROUND(
                ((COALESCE(pc.pos_days, 0)::NUMERIC + 2.0) * 100.0) /
                (COALESCE(pc.active_return_days, 0)::NUMERIC + 4.0),
                2
            ) AS calc_consistency_score,
            (
                COALESCE(pt.closed_total, 0) > 0
                OR COALESCE(pop.open_total, 0) > 0
                OR COALESCE(pc.active_return_days, 0) > 0
                OR ABS(ap.total_equity - seq.start_eq) > 0.01
            ) AS has_activity
        FROM active_portfolios ap
        LEFT JOIN model_decisions mdec ON mdec.m_name = ap.owner_id
        LEFT JOIN model_conviction mconv ON mconv.m_name = ap.owner_id
        LEFT JOIN portfolio_trades pt ON pt.portfolio_id = ap.id
        LEFT JOIN portfolio_open_positions pop ON pop.portfolio_id = ap.id
        LEFT JOIN starting_equities seq ON seq.portfolio_id = ap.id
        LEFT JOIN portfolio_consistency pc ON pc.portfolio_id = ap.id
    ),
    user_bot_metrics AS (
        SELECT
            ('user-bot:' || sr.id::TEXT) AS model_name,
            COALESCE(NULLIF(TRIM(sr.name), ''), 'Untitled Bot') AS display_name,
            'user_bot'::TEXT AS entity_type,
            NULL::UUID AS portfolio_id,
            sr.id AS recipe_id,
            COALESCE(sr.is_live, FALSE) AS is_live,
            COALESCE(ubs.total_equity, COALESCE(sr.paper_cash, 10000.00))::NUMERIC AS total_equity,
            COALESCE(ubs.return_pct, 0.00)::NUMERIC AS return_pct,
            COALESCE(ubs.realized_pnl, 0.00)::NUMERIC AS realized_pnl,
            ubs.win_rate AS win_rate,
            COALESCE(ubs.total_trades, 0::BIGINT) AS total_trades,
            NULL::NUMERIC AS average_confidence,
            NULL::NUMERIC AS conviction_score,
            100.00::NUMERIC AS api_success_rate,
            COALESCE(ubs.trading_activity_rate, 0.00)::NUMERIC AS trading_activity_rate,
            COALESCE(ubs.win_rate, 50.0)::NUMERIC AS effective_win_rate,
            COALESCE(ubs.consistency_score, 50.00)::NUMERIC AS calc_consistency_score,
            COALESCE(ubs.has_activity, FALSE) AS has_activity
        FROM public.strategy_recipes sr
        LEFT JOIN public.user_bot_leaderboard_stats ubs
            ON ubs.recipe_id = sr.id
           AND ubs.time_window_days = v_window_key
        WHERE sr.archived_at IS NULL
          AND sr.is_template = FALSE
          AND sr.is_public = TRUE
          AND sr.user_id <> '00000000-0000-0000-0000-000000000000'
          AND jsonb_typeof(sr.graph_json->'stages') = 'array'
          AND jsonb_array_length(sr.graph_json->'stages') = 1
    ),
    combined AS (
        SELECT * FROM portfolio_metrics
        UNION ALL
        SELECT * FROM user_bot_metrics
    ),
    scored AS (
        SELECT
            c.model_name,
            c.display_name,
            c.entity_type,
            c.portfolio_id,
            c.recipe_id,
            c.is_live,
            c.total_equity,
            c.return_pct,
            c.realized_pnl,
            c.win_rate,
            c.total_trades,
            c.average_confidence,
            c.conviction_score,
            c.api_success_rate,
            c.trading_activity_rate,
            CASE
                WHEN NOT c.has_activity THEN 0.00::NUMERIC
                ELSE ROUND(
                    (0.7 * LEAST(GREATEST(((c.return_pct + 15.0) / 30.0) * 100.0, 0.0), 100.0)) +
                    (0.3 * c.effective_win_rate),
                    2
                )
            END AS trading_performance_score,
            c.conviction_score AS reasoning_quality_score,
            c.calc_consistency_score AS consistency_score,
            c.has_activity
        FROM combined c
    )
    SELECT
        s.model_name,
        s.display_name,
        s.entity_type,
        s.portfolio_id,
        s.recipe_id,
        s.is_live,
        s.total_equity,
        s.return_pct,
        s.realized_pnl,
        s.win_rate,
        s.total_trades,
        s.average_confidence,
        s.conviction_score,
        s.api_success_rate,
        s.trading_activity_rate,
        s.trading_performance_score,
        s.reasoning_quality_score,
        s.consistency_score,
        CASE
            WHEN NOT s.has_activity THEN 0.00::NUMERIC
            WHEN s.entity_type = 'llm' THEN ROUND(
                (0.5 * s.trading_performance_score) +
                (0.3 * COALESCE(s.conviction_score, 50.0)) +
                (0.2 * s.consistency_score),
                2
            )
            ELSE ROUND(
                (0.7 * s.trading_performance_score) +
                (0.3 * s.consistency_score),
                2
            )
        END AS composite_score
    FROM scored s
    ORDER BY
        composite_score DESC,
        s.return_pct DESC,
        s.model_name ASC;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_llm_leaderboard_metrics(time_window_days INT) TO anon, authenticated, service_role;

-- 3. Server-side paginated STABLE GET-routable leaderboard page RPC ----------
DROP FUNCTION IF EXISTS public.get_leaderboard_page(INT, TEXT, TEXT, TEXT, INT, INT);

CREATE OR REPLACE FUNCTION public.get_leaderboard_page(
    p_time_window_days INT DEFAULT 30,
    p_category TEXT DEFAULT 'all',
    p_sort_by TEXT DEFAULT 'composite_score',
    p_sort_dir TEXT DEFAULT 'desc',
    p_limit INT DEFAULT 10,
    p_offset INT DEFAULT 0
)
RETURNS TABLE (
    model_name TEXT,
    display_name TEXT,
    entity_type TEXT,
    portfolio_id UUID,
    recipe_id UUID,
    is_live BOOLEAN,
    total_equity NUMERIC,
    return_pct NUMERIC,
    realized_pnl NUMERIC,
    win_rate NUMERIC,
    total_trades BIGINT,
    average_confidence NUMERIC,
    conviction_score NUMERIC,
    api_success_rate NUMERIC,
    trading_activity_rate NUMERIC,
    trading_performance_score NUMERIC,
    reasoning_quality_score NUMERIC,
    consistency_score NUMERIC,
    composite_score NUMERIC,
    rank BIGINT,
    total_count BIGINT,
    all_count BIGINT,
    llm_count BIGINT,
    system_count BIGINT,
    user_bot_count BIGINT,
    is_podium BOOLEAN,
    is_page_row BOOLEAN
) LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
DECLARE
    v_category TEXT := COALESCE(NULLIF(TRIM(p_category), ''), 'all');
    v_sort_by TEXT := COALESCE(NULLIF(TRIM(p_sort_by), ''), 'composite_score');
    v_sort_dir TEXT := LOWER(COALESCE(NULLIF(TRIM(p_sort_dir), ''), 'desc'));
    v_limit INT := LEAST(GREATEST(COALESCE(p_limit, 10), 1), 50);
    v_offset INT := GREATEST(COALESCE(p_offset, 0), 0);
BEGIN
    IF v_category NOT IN ('all', 'llm', 'system', 'user_bot') THEN
        v_category := 'all';
    END IF;
    IF v_sort_by NOT IN ('composite_score', 'return_pct', 'win_rate', 'consistency_score') THEN
        v_sort_by := 'composite_score';
    END IF;
    IF v_sort_dir NOT IN ('asc', 'desc') THEN
        v_sort_dir := 'desc';
    END IF;

    RETURN QUERY
    WITH base AS (
        SELECT * FROM public.get_llm_leaderboard_metrics(p_time_window_days)
    ),
    counts AS (
        SELECT
            COUNT(*)::BIGINT AS c_all,
            COUNT(*) FILTER (WHERE b.entity_type = 'llm')::BIGINT AS c_llm,
            COUNT(*) FILTER (WHERE b.entity_type = 'system')::BIGINT AS c_system,
            COUNT(*) FILTER (WHERE b.entity_type = 'user_bot')::BIGINT AS c_user_bot
        FROM base b
    ),
    filtered AS (
        SELECT
            b.*,
            ROW_NUMBER() OVER (ORDER BY b.composite_score DESC, b.return_pct DESC, b.model_name ASC) AS cat_rank,
            COUNT(*) OVER ()::BIGINT AS cat_total
        FROM base b
        WHERE v_category = 'all' OR b.entity_type = v_category
    ),
    ordered AS (
        SELECT
            f.*,
            ROW_NUMBER() OVER (
                ORDER BY
                    CASE WHEN v_sort_by = 'composite_score' AND v_sort_dir = 'asc' THEN f.composite_score END ASC NULLS LAST,
                    CASE WHEN v_sort_by = 'composite_score' AND v_sort_dir = 'desc' THEN f.composite_score END DESC NULLS LAST,
                    CASE WHEN v_sort_by = 'return_pct' AND v_sort_dir = 'asc' THEN f.return_pct END ASC NULLS LAST,
                    CASE WHEN v_sort_by = 'return_pct' AND v_sort_dir = 'desc' THEN f.return_pct END DESC NULLS LAST,
                    CASE WHEN v_sort_by = 'win_rate' AND v_sort_dir = 'asc' THEN f.win_rate END ASC NULLS LAST,
                    CASE WHEN v_sort_by = 'win_rate' AND v_sort_dir = 'desc' THEN f.win_rate END DESC NULLS LAST,
                    CASE WHEN v_sort_by = 'consistency_score' AND v_sort_dir = 'asc' THEN f.consistency_score END ASC NULLS LAST,
                    CASE WHEN v_sort_by = 'consistency_score' AND v_sort_dir = 'desc' THEN f.consistency_score END DESC NULLS LAST,
                    f.cat_rank ASC
            ) AS sort_pos
        FROM filtered f
    )
    SELECT
        o.model_name,
        o.display_name,
        o.entity_type,
        o.portfolio_id,
        o.recipe_id,
        o.is_live,
        o.total_equity,
        o.return_pct,
        o.realized_pnl,
        o.win_rate,
        o.total_trades,
        o.average_confidence,
        o.conviction_score,
        o.api_success_rate,
        o.trading_activity_rate,
        o.trading_performance_score,
        o.reasoning_quality_score,
        o.consistency_score,
        o.composite_score,
        o.cat_rank AS rank,
        o.cat_total AS total_count,
        cnt.c_all AS all_count,
        cnt.c_llm AS llm_count,
        cnt.c_system AS system_count,
        cnt.c_user_bot AS user_bot_count,
        (o.cat_rank <= 3) AS is_podium,
        (o.sort_pos > v_offset AND o.sort_pos <= v_offset + v_limit) AS is_page_row
    FROM ordered o
    CROSS JOIN counts cnt
    WHERE o.cat_rank <= 3
       OR (o.sort_pos > v_offset AND o.sort_pos <= v_offset + v_limit)
    ORDER BY
        o.sort_pos ASC,
        o.cat_rank ASC;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_leaderboard_page(INT, TEXT, TEXT, TEXT, INT, INT) TO anon, authenticated, service_role;

NOTIFY pgrst, 'reload schema';
