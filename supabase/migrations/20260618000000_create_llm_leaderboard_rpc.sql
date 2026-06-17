-- Migration: Create get_llm_leaderboard_metrics RPC for LLM Leaderboard
-- Created: 2026-06-18

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
END_WEEKDAYS INT;
BEGIN
    -- Determine the start date of the window
    IF time_window_days IS NOT NULL AND time_window_days > 0 THEN
        start_date := (NOW() - (time_window_days || ' days')::INTERVAL)::DATE;
    ELSE
        SELECT COALESCE(MIN(created_at)::DATE, CURRENT_DATE) INTO start_date FROM public.decisions;
    END IF;

    -- Calculate expected weekdays (Mon-Fri) in the range [start_date, end_date]
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
            -- verifier approval rate: status IN ('VALIDATED', 'EXECUTED', 'REJECTED_MARGIN', 'REJECTED_OWNERSHIP', 'REJECTED_REDUNDANCY', 'REJECTED_LIQUIDITY', 'REJECTED_MARKET_CLOSED', 'REJECTED_LIMIT_PRICE') divided by total non-error decisions
            COALESCE(
                (COUNT(CASE WHEN d.status IN ('VALIDATED', 'EXECUTED', 'REJECTED_MARGIN', 'REJECTED_OWNERSHIP', 'REJECTED_REDUNDANCY', 'REJECTED_LIQUIDITY', 'REJECTED_MARKET_CLOSED', 'REJECTED_LIMIT_PRICE') THEN 1 END)::NUMERIC * 100.0) /
                NULLIF(COUNT(CASE WHEN d.status != 'ERROR_PROVIDER' THEN 1 END), 0),
                0.0
            ) AS verifier_app_rate,
            
            -- average confidence: average of confidence from decisions
            COALESCE(AVG(d.confidence), 0.0) AS avg_conf,
            
            -- api success rate: non-error decisions / total decisions
            COALESCE(
                (COUNT(CASE WHEN d.status != 'ERROR_PROVIDER' THEN 1 END)::NUMERIC * 100.0) /
                NULLIF(COUNT(d.id), 0),
                0.0
            ) AS api_succ_rate,
            
            -- distinct days of attempts in the window
            COUNT(DISTINCT (d.created_at::DATE))::INT AS active_days
        FROM
            public.decisions d
        WHERE
            d.created_at >= start_date
        GROUP BY
            d.model_name
    ),
    model_trades AS (
        SELECT
            p.owner_id AS m_name,
            COALESCE(SUM(t.realized_pnl), 0.0) AS sum_realized_pnl,
            -- win rate: realized_pnl > 0 / total trades
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
    )
    SELECT
        port.owner_id AS model_name,
        port.total_equity,
        -- return % relative to $10,000.00
        ROUND(COALESCE(((port.total_equity - 10000.00) / 10000.00) * 100.0, 0.0), 2) AS return_pct,
        ROUND(COALESCE(mtrades.sum_realized_pnl, 0.0), 2) AS realized_pnl,
        ROUND(COALESCE(mtrades.t_win_rate, 0.0), 2) AS win_rate,
        COALESCE(mtrades.t_total_trades, 0::BIGINT) AS total_trades,
        ROUND(COALESCE(mdec.verifier_app_rate, 0.0), 2) AS verifier_approval_rate,
        ROUND(COALESCE(mdec.avg_conf, 0.0), 2) AS average_confidence,
        ROUND(COALESCE(mdec.api_succ_rate, 0.0), 2) AS api_success_rate,
        ROUND(COALESCE((mdec.active_days::NUMERIC / total_weekdays) * 100.0, 0.0), 2) AS trading_activity_rate,
        
        -- trading performance score: 70% return score + 30% win rate
        -- return score is mapped linearly from -15% (0 score) to +15% (100 score)
        ROUND(
            (0.7 * LEAST(GREATEST(((COALESCE(((port.total_equity - 10000.00) / 10000.00) * 100.0, 0.0) + 15.0) / 30.0) * 100.0, 0.0), 100.0)) +
            (0.3 * COALESCE(mtrades.t_win_rate, 0.0)),
            2
        ) AS trading_performance_score,
        
        -- reasoning quality score: 70% verifier approval rate + 30% average confidence
        ROUND(
            (0.7 * COALESCE(mdec.verifier_app_rate, 0.0)) +
            (0.3 * COALESCE(mdec.avg_conf, 0.0)),
            2
        ) AS reasoning_quality_score,
        
        -- consistency score: 70% api success rate + 30% trading activity rate (capped at 100.0)
        ROUND(
            (0.7 * COALESCE(mdec.api_succ_rate, 0.0)) +
            (0.3 * LEAST(COALESCE((mdec.active_days::NUMERIC / total_weekdays) * 100.0, 0.0), 100.0)),
            2
        ) AS consistency_score,
        
        -- composite score: 50% trading performance + 30% reasoning quality + 20% consistency
        ROUND(
            (0.5 * (
                (0.7 * LEAST(GREATEST(((COALESCE(((port.total_equity - 10000.00) / 10000.00) * 100.0, 0.0) + 15.0) / 30.0) * 100.0, 0.0), 100.0)) +
                (0.3 * COALESCE(mtrades.t_win_rate, 0.0))
            )) +
            (0.3 * (
                (0.7 * COALESCE(mdec.verifier_app_rate, 0.0)) +
                (0.3 * COALESCE(mdec.avg_conf, 0.0))
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
        model_trades mtrades ON mtrades.m_name = port.owner_id
    ORDER BY
        composite_score DESC;
END;
$$;

-- Explicitly grant execute permission to web client and engine roles
GRANT EXECUTE ON FUNCTION public.get_llm_leaderboard_metrics(time_window_days INT) TO anon, authenticated, service_role;
