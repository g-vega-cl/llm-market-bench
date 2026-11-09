-- Migration: Allow HOLD predicted_direction in daily_predictions and align conviction scoring
-- Created: 2026-11-09

-- 1. Drop existing check constraint and replace with UP, DOWN, HOLD
DO $$
DECLARE
    chk_name TEXT;
BEGIN
    SELECT conname INTO chk_name
    FROM pg_constraint
    WHERE conrelid = 'public.daily_predictions'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%predicted_direction%';

    IF chk_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE public.daily_predictions DROP CONSTRAINT ' || quote_ident(chk_name);
    END IF;
END $$;

ALTER TABLE public.daily_predictions
    ADD CONSTRAINT daily_predictions_predicted_direction_check
    CHECK (predicted_direction IN ('UP', 'DOWN', 'HOLD'));

-- 2. Update get_llm_leaderboard_metrics so HOLD predictions contribute neutral 0.0 CP
DROP FUNCTION IF EXISTS public.get_llm_leaderboard_metrics(INT);

CREATE OR REPLACE FUNCTION public.get_llm_leaderboard_metrics(time_window_days INT)
RETURNS TABLE (
    model_name TEXT,
    total_equity NUMERIC,
    return_pct NUMERIC,
    realized_pnl NUMERIC,
    win_rate NUMERIC,
    total_trades BIGINT,
    verifier_approval_rate NUMERIC,
    average_confidence NUMERIC,
    conviction_score NUMERIC,
    api_success_rate NUMERIC,
    trading_activity_rate NUMERIC,
    trading_performance_score NUMERIC,
    reasoning_quality_score NUMERIC,
    consistency_score NUMERIC,
    composite_score NUMERIC
) LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    start_date DATE;
    end_date DATE := CURRENT_DATE;
    total_weekdays INT;
BEGIN
    IF time_window_days IS NOT NULL AND time_window_days > 0 THEN
        start_date := (NOW() - (time_window_days || ' days')::INTERVAL)::DATE;
    ELSE
        SELECT COALESCE(MIN(created_at)::DATE, CURRENT_DATE) INTO start_date FROM public.decisions;
    END IF;

    SELECT COUNT(*)::INT INTO total_weekdays
    FROM generate_series(start_date, end_date, '1 day'::interval) d
    WHERE EXTRACT(isodow FROM d) < 6;

    IF total_weekdays <= 0 THEN
        total_weekdays := 1;
    END IF;

    RETURN QUERY
    WITH model_decisions AS (
        SELECT
            d.model_name AS m_name,
            COALESCE(
                (COUNT(CASE WHEN d.status IN ('VALIDATED', 'EXECUTED', 'REJECTED_MARGIN', 'REJECTED_OWNERSHIP', 'REJECTED_REDUNDANCY', 'REJECTED_LIQUIDITY', 'REJECTED_MARKET_CLOSED', 'REJECTED_LIMIT_PRICE') THEN 1 END)::NUMERIC * 100.0) /
                NULLIF(COUNT(CASE WHEN d.status != 'ERROR_PROVIDER' THEN 1 END), 0),
                0.0
            ) AS verifier_app_rate,
            COALESCE(AVG(d.confidence), 0.0) AS avg_conf,
            COALESCE(
                (COUNT(CASE WHEN d.status != 'ERROR_PROVIDER' THEN 1 END)::NUMERIC * 100.0) /
                NULLIF(COUNT(d.id), 0),
                0.0
            ) AS api_succ_rate,
            COUNT(DISTINCT (d.created_at::DATE))::INT AS active_days
        FROM
            public.decisions d
        WHERE
            d.created_at >= start_date
        GROUP BY
            d.model_name
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
            FROM
                public.daily_predictions dp
            WHERE
                dp.status = 'evaluated'
                AND dp.target_date >= start_date
            GROUP BY
                dp.model_name
        ) mc
    ),
    model_trades AS (
        SELECT
            p.owner_id AS m_name,
            COALESCE(SUM(t.realized_pnl), 0.0) AS sum_realized_pnl,
            COALESCE(
                (COUNT(CASE WHEN t.realized_pnl > 0 THEN 1 END)::NUMERIC * 100.0) /
                NULLIF(COUNT(t.id), 0),
                0.0
            ) AS t_win_rate,
            COUNT(t.id)::BIGINT AS t_total_trades
        FROM
            public.portfolios p
        LEFT JOIN
            public.trades t ON t.portfolio_id = p.id AND t.executed_at >= start_date
        GROUP BY
            p.owner_id
    ),
    starting_equities AS (
        SELECT
            p.owner_id AS m_name,
            COALESCE(
                (SELECT pe.total_equity
                 FROM public.portfolio_performance pe
                 WHERE pe.portfolio_id = p.id AND pe.date <= start_date
                 ORDER BY pe.date DESC
                 LIMIT 1),
                (SELECT pe.total_equity
                 FROM public.portfolio_performance pe
                 WHERE pe.portfolio_id = p.id AND pe.date >= start_date
                 ORDER BY pe.date ASC
                 LIMIT 1),
                10000.00
            ) AS start_eq
        FROM
            public.portfolios p
    )
    SELECT
        port.owner_id AS model_name,
        port.total_equity,
        ROUND(COALESCE(((port.total_equity - seq.start_eq) / NULLIF(seq.start_eq, 0)) * 100.0, 0.0), 2) AS return_pct,
        ROUND(COALESCE(mtrades.sum_realized_pnl, 0.0), 2) AS realized_pnl,
        ROUND(COALESCE(mtrades.t_win_rate, 0.0), 2) AS win_rate,
        COALESCE(mtrades.t_total_trades, 0::BIGINT) AS total_trades,
        CASE
            WHEN port.owner_id = 'MiniMax-M3' THEN NULL
            ELSE ROUND(COALESCE(mdec.verifier_app_rate, 0.0), 2)
        END AS verifier_approval_rate,
        ROUND(COALESCE(mdec.avg_conf, 0.0), 2) AS average_confidence,
        -- Neutral 50.0 for models with no evaluated daily predictions.
        ROUND(COALESCE(mconv.conviction_norm, 50.0)::NUMERIC, 2) AS conviction_score,
        ROUND(COALESCE(mdec.api_succ_rate, 0.0), 2) AS api_success_rate,
        ROUND(COALESCE((mdec.active_days::NUMERIC / total_weekdays) * 100.0, 0.0), 2) AS trading_activity_rate,

        ROUND(
            (0.7 * LEAST(GREATEST(((COALESCE(((port.total_equity - seq.start_eq) / NULLIF(seq.start_eq, 0)) * 100.0, 0.0) + 15.0) / 30.0) * 100.0, 0.0), 100.0)) +
            (0.3 * COALESCE(mtrades.t_win_rate, 0.0)),
            2
        ) AS trading_performance_score,

        -- reasoning quality: 70% verifier approval + 30% conviction.
        -- For MiniMax-M3 the verifier is not used, so conviction stands alone.
        CASE
            WHEN port.owner_id = 'MiniMax-M3' THEN
                ROUND(COALESCE(mconv.conviction_norm, 50.0)::NUMERIC, 2)
            ELSE
                ROUND(
                    (0.7 * COALESCE(mdec.verifier_app_rate, 0.0)) +
                    (0.3 * COALESCE(mconv.conviction_norm, 50.0)),
                    2
                )
        END AS reasoning_quality_score,

        ROUND(
            (0.7 * COALESCE(mdec.api_succ_rate, 0.0)) +
            (0.3 * LEAST(COALESCE((mdec.active_days::NUMERIC / total_weekdays) * 100.0, 0.0), 100.0)),
            2
        ) AS consistency_score,

        ROUND(
            (0.5 * (
                (0.7 * LEAST(GREATEST(((COALESCE(((port.total_equity - seq.start_eq) / NULLIF(seq.start_eq, 0)) * 100.0, 0.0) + 15.0) / 30.0) * 100.0, 0.0), 100.0)) +
                (0.3 * COALESCE(mtrades.t_win_rate, 0.0))
            )) +
            (0.3 * (
                CASE
                    WHEN port.owner_id = 'MiniMax-M3' THEN COALESCE(mconv.conviction_norm, 50.0)
                    ELSE
                        (0.7 * COALESCE(mdec.verifier_app_rate, 0.0)) +
                        (0.3 * COALESCE(mconv.conviction_norm, 50.0))
                END
            )) +
            (0.2 * (
                (0.7 * COALESCE(mdec.api_succ_rate, 0.0)) +
                (0.3 * LEAST(COALESCE((mdec.active_days::NUMERIC / total_weekdays) * 100.0, 0.0), 100.0))
            )),
            2
        ) AS composite_score
    FROM
        public.portfolios port
    LEFT JOIN
        model_decisions mdec ON mdec.m_name = port.owner_id
    LEFT JOIN
        model_conviction mconv ON mconv.m_name = port.owner_id
    LEFT JOIN
        model_trades mtrades ON mtrades.m_name = port.owner_id
    LEFT JOIN
        starting_equities seq ON seq.m_name = port.owner_id
    ORDER BY
        composite_score DESC;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_llm_leaderboard_metrics(time_window_days INT) TO anon, authenticated, service_role;
