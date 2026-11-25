-- ============================================================================
-- Migration: 20261125000000_unified_leaderboard_and_public_bots.sql
-- Description:
--   1. Make all non-archived user bots (`strategy_recipes`) public by default and
--      backfill existing valid non-archived user bots so all user bots appear publicly.
--   2. Add safe ISO date parser `public._safe_iso_date(TEXT)` so malformed JSONB
--      timestamps never crash queries.
--   3. Update `get_llm_leaderboard_metrics(time_window_days INT)` as STABLE (GET-routable
--      to read replicas) to:
--      a) Remove verifier approval column and scoring (no verifier active) and
--         score reasoning quality from `conviction_score` alone.
--      b) Fix `win_rate`: combine closed exit trades (`SELL`/`COVER` with non-null
--         `realized_pnl`) and open positions (`position_pnl`), excluding entry
--         `BUY` rows from the denominator; return NULL when neither exists.
--      c) Replace uptime-based `consistency_score` (~100% everywhere) with
--         Laplace-smoothed daily equity return consistency (% of active trading
--         days with positive daily return from `portfolio_performance` /
--         `paper_equity_curve`).
--      d) Include active `sys-*` system portfolios (excluding archived ids) and
--         all public non-archived user bots (`strategy_recipes`) alongside LLMs,
--         ranking idle 0-activity bots at 0.00 below active competitors.
-- ============================================================================

-- 1. Ensure all valid user bots are public -----------------------------------
ALTER TABLE public.strategy_recipes
    ALTER COLUMN is_public SET DEFAULT TRUE;

UPDATE public.strategy_recipes
SET is_public = TRUE
WHERE archived_at IS NULL
  AND is_public IS DISTINCT FROM TRUE
  AND user_id <> '00000000-0000-0000-0000-000000000000'
  AND jsonb_typeof(graph_json->'stages') = 'array'
  AND jsonb_array_length(graph_json->'stages') = 1;

-- 2. Safe ISO date helper (guards against impossible calendar dates) ---------
CREATE OR REPLACE FUNCTION public._safe_iso_date(val TEXT)
RETURNS DATE
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF val IS NOT NULL AND val ~ '^\d{4}-\d{2}-\d{2}' THEN
        RETURN LEFT(val, 10)::DATE;
    END IF;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$;

REVOKE ALL ON FUNCTION public._safe_iso_date(TEXT) FROM PUBLIC;

-- 3. Unified STABLE leaderboard RPC ------------------------------------------
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
BEGIN
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
    WITH archived_owners(owner_id) AS (
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
            p.total_equity
        FROM public.portfolios p
        WHERE p.owner_id NOT IN (SELECT owner_id FROM archived_owners)
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
            )::BIGINT AS closed_total,
            COUNT(t.id)::BIGINT AS t_total_trades
        FROM active_portfolios ap
        LEFT JOIN public.trades t
            ON t.portfolio_id = ap.id
           AND t.executed_at >= start_date
        GROUP BY ap.id
    ),
    portfolio_open_positions AS (
        SELECT
            pp.portfolio_id,
            COUNT(CASE WHEN pp.unrealized_pnl_usd > 0 THEN 1 END)::BIGINT AS open_wins,
            COUNT(pp.position_id)::BIGINT AS open_total
        FROM public.position_pnl pp
        GROUP BY pp.portfolio_id
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
            CASE
                WHEN LOWER(ap.owner_id) LIKE 'sys-%' OR LOWER(ap.owner_id) LIKE 'sys\_%' ESCAPE '\' THEN 'system'
                ELSE 'llm'
            END AS entity_type,
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
            COALESCE(pt.t_total_trades, 0::BIGINT) AS total_trades,
            ROUND(COALESCE(mdec.avg_conf, 0.0), 2) AS average_confidence,
            ROUND(COALESCE(mconv.conviction_norm, 50.0)::NUMERIC, 2) AS conviction_score,
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
                COALESCE(pt.t_total_trades, 0) > 0
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
    user_bots_base AS (
        SELECT
            sr.id AS recipe_id,
            COALESCE(NULLIF(TRIM(sr.name), ''), 'Untitled Bot') AS bot_name,
            COALESCE(sr.is_live, FALSE) AS is_live,
            COALESCE(sr.paper_cash, 10000.0)::NUMERIC AS paper_cash,
            CASE
                WHEN jsonb_typeof(sr.paper_positions) = 'array' THEN sr.paper_positions
                ELSE '[]'::jsonb
            END AS paper_positions,
            CASE
                WHEN jsonb_typeof(sr.paper_trades) = 'array' THEN sr.paper_trades
                ELSE '[]'::jsonb
            END AS paper_trades,
            CASE
                WHEN jsonb_typeof(sr.paper_equity_curve) = 'array' THEN sr.paper_equity_curve
                ELSE '[]'::jsonb
            END AS paper_equity_curve
        FROM public.strategy_recipes sr
        WHERE sr.archived_at IS NULL
          AND sr.is_template = FALSE
          AND sr.is_public = TRUE
          AND sr.user_id <> '00000000-0000-0000-0000-000000000000'
          AND jsonb_typeof(sr.graph_json->'stages') = 'array'
          AND jsonb_array_length(sr.graph_json->'stages') = 1
    ),
    bot_curve_points AS (
        SELECT
            ub.recipe_id,
            pt.ord,
            public._safe_iso_date(pt.elem->>'time') AS pt_date,
            (pt.elem->>'equity')::NUMERIC AS equity
        FROM user_bots_base ub
        CROSS JOIN LATERAL jsonb_array_elements(ub.paper_equity_curve) WITH ORDINALITY AS pt(elem, ord)
        WHERE public._safe_iso_date(pt.elem->>'time') IS NOT NULL
          AND (pt.elem->>'equity') ~ '^-?\d+(\.\d+)?$'
    ),
    bot_daily_close AS (
        SELECT DISTINCT ON (bcp.recipe_id, bcp.pt_date)
            bcp.recipe_id,
            bcp.pt_date,
            bcp.equity
        FROM bot_curve_points bcp
        ORDER BY bcp.recipe_id, bcp.pt_date ASC, bcp.ord DESC
    ),
    bot_daily_ordered AS (
        SELECT
            bdc.recipe_id,
            bdc.pt_date,
            bdc.equity,
            LAG(bdc.equity) OVER (PARTITION BY bdc.recipe_id ORDER BY bdc.pt_date ASC) AS prev_equity
        FROM bot_daily_close bdc
    ),
    bot_consistency AS (
        SELECT
            bdo.recipe_id,
            COUNT(CASE WHEN bdo.equity > bdo.prev_equity THEN 1 END)::BIGINT AS pos_days,
            COUNT(*)::BIGINT AS active_return_days
        FROM bot_daily_ordered bdo
        WHERE bdo.pt_date >= start_date
          AND bdo.prev_equity IS NOT NULL
          AND bdo.prev_equity > 0
          AND bdo.equity <> bdo.prev_equity
        GROUP BY bdo.recipe_id
    ),
    bot_positions_summary AS (
        SELECT
            ub.recipe_id,
            COALESCE(
                SUM(
                    CASE
                        WHEN (pos.elem->>'market_value') ~ '^-?\d+(\.\d+)?$'
                            THEN (pos.elem->>'market_value')::NUMERIC
                        WHEN (pos.elem->>'shares') ~ '^-?\d+(\.\d+)?$'
                         AND COALESCE(NULLIF(pos.elem->>'current_price', ''), NULLIF(pos.elem->>'entry_price', '')) ~ '^-?\d+(\.\d+)?$'
                            THEN (pos.elem->>'shares')::NUMERIC * COALESCE(NULLIF(pos.elem->>'current_price', ''), NULLIF(pos.elem->>'entry_price', ''))::NUMERIC
                        ELSE 0.0
                    END
                ),
                0.0
            ) AS positions_value,
            COUNT(
                CASE
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
                    ) > 0
                        THEN 1
                END
            )::BIGINT AS open_wins,
            COUNT(*)::BIGINT AS open_total
        FROM user_bots_base ub
        CROSS JOIN LATERAL jsonb_array_elements(ub.paper_positions) AS pos(elem)
        GROUP BY ub.recipe_id
    ),
    bot_trades_summary AS (
        SELECT
            ub.recipe_id,
            COALESCE(SUM((tr.elem->>'pnl_net')::NUMERIC), 0.0) AS sum_realized_pnl,
            COUNT(CASE WHEN (tr.elem->>'pnl_net')::NUMERIC > 0 THEN 1 END)::BIGINT AS closed_wins,
            COUNT(*)::BIGINT AS closed_total
        FROM user_bots_base ub
        CROSS JOIN LATERAL jsonb_array_elements(ub.paper_trades) AS tr(elem)
        WHERE (tr.elem->>'pnl_net') ~ '^-?\d+(\.\d+)?$'
          AND (
              time_window_days IS NULL
              OR time_window_days <= 0
              OR public._safe_iso_date(COALESCE(NULLIF(tr.elem->>'exit_time', ''), NULLIF(tr.elem->>'entry_time', ''))) >= start_date
          )
        GROUP BY ub.recipe_id
    ),
    bot_equities AS (
        SELECT
            ub.recipe_id,
            COALESCE(
                (SELECT bcp.equity
                 FROM bot_curve_points bcp
                 WHERE bcp.recipe_id = ub.recipe_id
                 ORDER BY bcp.pt_date DESC, bcp.ord DESC
                 LIMIT 1),
                ub.paper_cash + COALESCE(bps.positions_value, 0.0),
                10000.00
            ) AS last_eq,
            COALESCE(
                (SELECT bdc.equity
                 FROM bot_daily_close bdc
                 WHERE bdc.recipe_id = ub.recipe_id AND bdc.pt_date <= start_date
                 ORDER BY bdc.pt_date DESC
                 LIMIT 1),
                10000.00
            ) AS start_eq
        FROM user_bots_base ub
        LEFT JOIN bot_positions_summary bps ON bps.recipe_id = ub.recipe_id
    ),
    user_bot_metrics AS (
        SELECT
            ('user-bot:' || ub.recipe_id::TEXT) AS model_name,
            ub.bot_name AS display_name,
            'user_bot'::TEXT AS entity_type,
            NULL::UUID AS portfolio_id,
            ub.recipe_id AS recipe_id,
            ub.is_live AS is_live,
            ROUND(beq.last_eq, 2) AS total_equity,
            ROUND(COALESCE(((beq.last_eq - beq.start_eq) / NULLIF(beq.start_eq, 0)) * 100.0, 0.0), 2) AS return_pct,
            ROUND(COALESCE(bts.sum_realized_pnl, 0.0), 2) AS realized_pnl,
            CASE
                WHEN (COALESCE(bts.closed_total, 0) + COALESCE(bps.open_total, 0)) > 0 THEN
                    ROUND(
                        ((COALESCE(bts.closed_wins, 0) + COALESCE(bps.open_wins, 0))::NUMERIC * 100.0) /
                        (COALESCE(bts.closed_total, 0) + COALESCE(bps.open_total, 0)),
                        2
                    )
                ELSE NULL::NUMERIC
            END AS win_rate,
            COALESCE(bts.closed_total, 0::BIGINT) AS total_trades,
            0.00::NUMERIC AS average_confidence,
            50.00::NUMERIC AS conviction_score,
            100.00::NUMERIC AS api_success_rate,
            ROUND(
                LEAST(
                    COALESCE((COALESCE(bc.active_return_days, 0)::NUMERIC / total_weekdays) * 100.0, 0.0),
                    100.0
                ),
                2
            ) AS trading_activity_rate,
            CASE
                WHEN (COALESCE(bts.closed_total, 0) + COALESCE(bps.open_total, 0)) > 0 THEN
                    ((COALESCE(bts.closed_wins, 0) + COALESCE(bps.open_wins, 0))::NUMERIC * 100.0) /
                    (COALESCE(bts.closed_total, 0) + COALESCE(bps.open_total, 0))
                ELSE 50.0
            END AS effective_win_rate,
            ROUND(
                ((COALESCE(bc.pos_days, 0)::NUMERIC + 2.0) * 100.0) /
                (COALESCE(bc.active_return_days, 0)::NUMERIC + 4.0),
                2
            ) AS calc_consistency_score,
            (
                COALESCE(bts.closed_total, 0) > 0
                OR COALESCE(bps.open_total, 0) > 0
                OR COALESCE(bc.active_return_days, 0) > 0
                OR ABS(beq.last_eq - beq.start_eq) > 0.01
            ) AS has_activity
        FROM user_bots_base ub
        LEFT JOIN bot_equities beq ON beq.recipe_id = ub.recipe_id
        LEFT JOIN bot_trades_summary bts ON bts.recipe_id = ub.recipe_id
        LEFT JOIN bot_positions_summary bps ON bps.recipe_id = ub.recipe_id
        LEFT JOIN bot_consistency bc ON bc.recipe_id = ub.recipe_id
    ),
    combined AS (
        SELECT * FROM portfolio_metrics
        UNION ALL
        SELECT * FROM user_bot_metrics
    )
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
        CASE
            WHEN NOT c.has_activity THEN 0.00::NUMERIC
            ELSE ROUND(
                (0.5 * (
                    (0.7 * LEAST(GREATEST(((c.return_pct + 15.0) / 30.0) * 100.0, 0.0), 100.0)) +
                    (0.3 * c.effective_win_rate)
                )) +
                (0.3 * c.conviction_score) +
                (0.2 * c.calc_consistency_score),
                2
            )
        END AS composite_score
    FROM combined c
    ORDER BY
        composite_score DESC,
        c.return_pct DESC;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_llm_leaderboard_metrics(time_window_days INT) TO anon, authenticated, service_role;

NOTIFY pgrst, 'reload schema';
