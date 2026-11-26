-- Enforce Alpaca trade state-machine transitions, cross-column invariants,
-- backfill structurally non-mirrored NULL rows to NO_MIRROR, and let
-- execute_portfolio_trade accept p_alpaca_status at insert time.

-- 1. Backfill structurally non-mirrored NULL trades so repair never scans them.
UPDATE public.trades t
SET alpaca_status = 'NO_MIRROR'
FROM public.portfolios p
WHERE p.id = t.portfolio_id
  AND t.alpaca_status IS NULL
  AND t.alpaca_order_id IS NULL
  AND (
      p.owner_id LIKE 'sys-daily-tlt-%'
      OR (p.owner_id LIKE 'sys-picks-%' AND UPPER(t.signal) IN ('SHORT', 'SELL', 'COVER'))
      OR (p.owner_id LIKE 'sys-daily-spy%' AND UPPER(t.signal) IN ('SHORT', 'COVER'))
      OR (p.owner_id LIKE 'sys-sector-%' AND UPPER(t.signal) IN ('SHORT', 'COVER'))
      OR p.owner_id LIKE 'lin-renko-agent-%'
      OR p.owner_id = 'sys-frontier-tech'
  );

-- 2. Cross-column CHECK invariants across alpaca_status, order_id, and timestamps.
ALTER TABLE public.trades
    DROP CONSTRAINT IF EXISTS trades_alpaca_columns_check;

ALTER TABLE public.trades
    ADD CONSTRAINT trades_alpaca_columns_check
    CHECK (
        (
            alpaca_status IN ('SUBMITTED', 'CANCELED', 'EXPIRED')
            AND alpaca_order_id IS NOT NULL
            AND alpaca_submitted_at IS NOT NULL
        )
        OR (
            alpaca_status = 'FILLED'
            AND alpaca_order_id IS NOT NULL
            AND alpaca_submitted_at IS NOT NULL
            AND alpaca_filled_at IS NOT NULL
        )
        OR (
            alpaca_status = 'REJECTED'
        )
        OR (
            (
                alpaca_status IS NULL
                OR alpaca_status IN ('ERROR', 'SKIPPED_NO_POSITION', 'DISABLED', 'BACKFILLED', 'NO_MIRROR')
            )
            AND alpaca_order_id IS NULL
        )
    ) NOT VALID;

ALTER TABLE public.trades
    VALIDATE CONSTRAINT trades_alpaca_columns_check;

-- 3. Enforce valid alpaca_status state transitions at the DB layer.
CREATE OR REPLACE FUNCTION public.enforce_trades_alpaca_status_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.alpaca_status IS NOT DISTINCT FROM NEW.alpaca_status THEN
        RETURN NEW;
    END IF;

    IF current_setting('app.allow_alpaca_status_override', true) = 'true' THEN
        RETURN NEW;
    END IF;

    IF OLD.alpaca_status IS NULL THEN
        RETURN NEW;
    END IF;

    IF OLD.alpaca_status = 'ERROR' AND NEW.alpaca_status IN ('SUBMITTED', 'FILLED', 'CANCELED', 'EXPIRED', 'REJECTED') THEN
        RETURN NEW;
    END IF;

    IF OLD.alpaca_status = 'SUBMITTED' AND NEW.alpaca_status IN ('FILLED', 'CANCELED', 'EXPIRED', 'REJECTED') THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'Invalid alpaca_status transition from % to % for trade %',
        COALESCE(OLD.alpaca_status, '<NULL>'),
        COALESCE(NEW.alpaca_status, '<NULL>'),
        OLD.id
        USING ERRCODE = 'check_violation';
END;
$$;

DROP TRIGGER IF EXISTS trg_enforce_trades_alpaca_status_transition ON public.trades;

CREATE TRIGGER trg_enforce_trades_alpaca_status_transition
    BEFORE UPDATE OF alpaca_status ON public.trades
    FOR EACH ROW
    EXECUTE FUNCTION public.enforce_trades_alpaca_status_transition();

-- 4. Allow execute_portfolio_trade RPC to stamp p_alpaca_status (e.g. NO_MIRROR) at insert time.
DROP FUNCTION IF EXISTS public.execute_portfolio_trade(
    UUID, TEXT, TEXT, INTEGER, NUMERIC, UUID, TEXT, UUID, JSONB
);
DROP FUNCTION IF EXISTS public.execute_portfolio_trade(
    UUID, TEXT, TEXT, INTEGER, NUMERIC, UUID, TEXT, UUID, JSONB, TEXT
);

CREATE OR REPLACE FUNCTION public.execute_portfolio_trade(
    p_portfolio_id UUID,
    p_ticker TEXT,
    p_signal TEXT,
    p_quantity INTEGER,
    p_price NUMERIC,
    p_decision_id UUID DEFAULT NULL,
    p_reason TEXT DEFAULT NULL,
    p_idempotency_key UUID DEFAULT NULL,
    p_mark_prices JSONB DEFAULT NULL,
    p_alpaca_status TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_ticker TEXT := UPPER(BTRIM(COALESCE(p_ticker, '')));
    v_signal TEXT := UPPER(BTRIM(COALESCE(p_signal, '')));
    v_alpaca_status TEXT := NULLIF(UPPER(BTRIM(COALESCE(p_alpaca_status, ''))), '');
    v_cash NUMERIC;
    v_sma NUMERIC;
    v_total_equity NUMERIC;
    v_pos_id UUID;
    v_pos_qty INTEGER := 0;
    v_pos_avg_cost NUMERIC := 0;
    v_exec_qty INTEGER;
    v_total_cost NUMERIC;
    v_new_cash NUMERIC;
    v_new_sma NUMERIC;
    v_new_pos_qty INTEGER := 0;
    v_new_avg_cost NUMERIC := 0;
    v_realized_pnl NUMERIC := NULL;
    v_realized_pnl_pct NUMERIC := NULL;
    v_positions_cost NUMERIC := 0;
    v_positions_mv NUMERIC := 0;
    v_new_realized NUMERIC;
    v_new_total_equity NUMERIC;
    v_trade_id UUID;
    v_existing RECORD;
BEGIN
    IF v_ticker = '' THEN
        RAISE EXCEPTION 'Ticker must be non-empty';
    END IF;
    IF v_signal NOT IN ('BUY', 'SELL') THEN
        RAISE EXCEPTION 'Invalid trade signal: %', p_signal;
    END IF;
    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        RAISE EXCEPTION 'Quantity must be positive, got %', p_quantity;
    END IF;
    IF p_price IS NULL OR p_price = 'NaN'::numeric OR p_price <= 0 OR p_price > 1000000000 THEN
        RAISE EXCEPTION 'Price must be finite and positive, got %', p_price;
    END IF;

    -- Serialize concurrent trades for the same portfolio row
    SELECT cash_balance, sma, total_equity
    INTO v_cash, v_sma, v_total_equity
    FROM public.portfolios
    WHERE id = p_portfolio_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Portfolio % not found', p_portfolio_id;
    END IF;

    -- Idempotent replay guard for retried HTTP/RPC requests
    IF p_idempotency_key IS NOT NULL THEN
        SELECT id, portfolio_id, ticker, quantity, total_cost, realized_pnl, realized_pnl_pct
        INTO v_existing
        FROM public.trades
        WHERE idempotency_key = p_idempotency_key;

        IF FOUND THEN
            IF v_existing.portfolio_id <> p_portfolio_id OR UPPER(v_existing.ticker) <> v_ticker THEN
                RAISE EXCEPTION 'Idempotency key % already used by another trade', p_idempotency_key;
            END IF;

            SELECT COALESCE(quantity, 0), COALESCE(average_cost_basis, 0)
            INTO v_new_pos_qty, v_new_avg_cost
            FROM public.portfolio_positions
            WHERE portfolio_id = p_portfolio_id AND ticker = v_ticker;

            RETURN jsonb_build_object(
                'trade_id', v_existing.id,
                'cash_balance', v_cash,
                'sma', v_sma,
                'total_equity', v_total_equity,
                'quantity', v_existing.quantity,
                'total_cost', v_existing.total_cost,
                'realized_pnl', v_existing.realized_pnl,
                'realized_pnl_pct', v_existing.realized_pnl_pct,
                'position_quantity', COALESCE(v_new_pos_qty, 0),
                'position_avg_cost', COALESCE(v_new_avg_cost, 0),
                'idempotent_replay', TRUE
            );
        END IF;
    END IF;

    SELECT id, quantity, average_cost_basis
    INTO v_pos_id, v_pos_qty, v_pos_avg_cost
    FROM public.portfolio_positions
    WHERE portfolio_id = p_portfolio_id AND ticker = v_ticker
    FOR UPDATE;

    IF v_signal = 'BUY' THEN
        v_exec_qty := p_quantity;
        v_total_cost := p_price * v_exec_qty;

        IF v_total_cost > v_cash THEN
            RAISE EXCEPTION 'Insufficient cash balance: need %, available %', v_total_cost, v_cash;
        END IF;

        v_new_cash := v_cash - v_total_cost;
        v_new_sma := GREATEST(0, v_new_cash);

        IF v_pos_id IS NOT NULL THEN
            v_new_pos_qty := v_pos_qty + v_exec_qty;
            v_new_avg_cost := ((v_pos_avg_cost * v_pos_qty) + v_total_cost) / v_new_pos_qty;
            UPDATE public.portfolio_positions
            SET quantity = v_new_pos_qty,
                average_cost_basis = v_new_avg_cost,
                last_updated_at = now()
            WHERE id = v_pos_id;
        ELSE
            v_new_pos_qty := v_exec_qty;
            v_new_avg_cost := p_price;
            INSERT INTO public.portfolio_positions (
                portfolio_id, ticker, quantity, average_cost_basis, last_updated_at
            )
            VALUES (
                p_portfolio_id, v_ticker, v_new_pos_qty, v_new_avg_cost, now()
            );
        END IF;
    ELSE
        -- SELL
        IF v_pos_id IS NULL OR v_pos_qty <= 0 THEN
            RAISE EXCEPTION 'Position % not held in portfolio %', v_ticker, p_portfolio_id;
        END IF;

        v_exec_qty := LEAST(p_quantity, v_pos_qty);
        v_total_cost := p_price * v_exec_qty;
        v_new_cash := v_cash + v_total_cost;
        v_new_sma := GREATEST(0, v_new_cash);
        v_realized_pnl := (p_price - v_pos_avg_cost) * v_exec_qty;
        v_realized_pnl_pct := CASE
            WHEN v_pos_avg_cost > 0 THEN ((p_price / v_pos_avg_cost) - 1) * 100
            ELSE 0
        END;

        v_new_pos_qty := v_pos_qty - v_exec_qty;
        IF v_new_pos_qty = 0 THEN
            DELETE FROM public.portfolio_positions WHERE id = v_pos_id;
            v_new_avg_cost := 0;
        ELSE
            v_new_avg_cost := v_pos_avg_cost;
            UPDATE public.portfolio_positions
            SET quantity = v_new_pos_qty,
                last_updated_at = now()
            WHERE id = v_pos_id;
        END IF;
    END IF;

    INSERT INTO public.trades (
        portfolio_id,
        ticker,
        signal,
        quantity,
        price,
        total_cost,
        executed_at,
        decision_id,
        reasoning,
        realized_pnl,
        realized_pnl_pct,
        idempotency_key,
        alpaca_status
    )
    VALUES (
        p_portfolio_id,
        v_ticker,
        v_signal,
        v_exec_qty,
        p_price,
        v_total_cost,
        now(),
        p_decision_id,
        p_reason,
        v_realized_pnl,
        v_realized_pnl_pct,
        p_idempotency_key,
        v_alpaca_status
    )
    RETURNING id INTO v_trade_id;

    -- Derive authoritative cash-only Reg-T metrics and total_equity from locked post-trade state
    SELECT
        COALESCE(SUM(quantity * average_cost_basis), 0),
        COALESCE(SUM(
            quantity * CASE
                WHEN p_mark_prices IS NOT NULL
                    AND (p_mark_prices ->> UPPER(ticker)) IS NOT NULL
                    AND (p_mark_prices ->> UPPER(ticker))::numeric <> 'NaN'::numeric
                    AND (p_mark_prices ->> UPPER(ticker))::numeric > 0
                THEN (p_mark_prices ->> UPPER(ticker))::numeric
                WHEN UPPER(ticker) = v_ticker THEN p_price
                ELSE average_cost_basis
            END
        ), 0)
    INTO v_positions_cost, v_positions_mv
    FROM public.portfolio_positions
    WHERE portfolio_id = p_portfolio_id;

    v_new_realized := v_new_cash + v_positions_cost;
    v_new_total_equity := v_new_cash + v_positions_mv;

    UPDATE public.portfolios
    SET cash_balance = v_new_cash,
        sma = v_new_sma,
        total_equity = v_new_total_equity,
        buying_power = v_new_sma,
        excess_liquidity = v_new_sma,
        maintenance_margin = 0,
        realized = v_new_realized,
        last_updated_at = now()
    WHERE id = p_portfolio_id;

    RETURN jsonb_build_object(
        'trade_id', v_trade_id,
        'cash_balance', v_new_cash,
        'sma', v_new_sma,
        'total_equity', v_new_total_equity,
        'quantity', v_exec_qty,
        'total_cost', v_total_cost,
        'realized_pnl', v_realized_pnl,
        'realized_pnl_pct', v_realized_pnl_pct,
        'position_quantity', v_new_pos_qty,
        'position_avg_cost', v_new_avg_cost,
        'idempotent_replay', FALSE
    );
END;
$$;

REVOKE ALL ON FUNCTION public.execute_portfolio_trade(
    UUID, TEXT, TEXT, INTEGER, NUMERIC, UUID, TEXT, UUID, JSONB, TEXT
) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.execute_portfolio_trade(
    UUID, TEXT, TEXT, INTEGER, NUMERIC, UUID, TEXT, UUID, JSONB, TEXT
) TO service_role;

COMMENT ON FUNCTION public.execute_portfolio_trade(
    UUID, TEXT, TEXT, INTEGER, NUMERIC, UUID, TEXT, UUID, JSONB, TEXT
) IS 'Atomically executes a BUY/SELL trade across portfolio_positions, trades, and portfolios with row locking, SQL-derived Reg-T/equity metrics, idempotency_key deduplication, and optional alpaca_status.';

NOTIFY pgrst, 'reload schema';
