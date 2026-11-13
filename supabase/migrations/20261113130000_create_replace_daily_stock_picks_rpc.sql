-- Migration: Atomic replacement of a daily stock basket's picks
-- Purpose: delete + insert of the 6 picks must be one transaction, so a crash or
-- 409 between the two PostgREST round-trips can never leave a basket with 0 picks.

CREATE OR REPLACE FUNCTION public.replace_daily_stock_picks(
    p_basket_id UUID,
    p_picks JSONB
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    DELETE FROM public.daily_stock_picks WHERE basket_id = p_basket_id;

    INSERT INTO public.daily_stock_picks (
        basket_id,
        target_date,
        model_name,
        ticker,
        direction,
        rank,
        confidence,
        expected_return_pct,
        reasoning,
        status
    )
    SELECT
        p_basket_id,
        (pick ->> 'target_date')::date,
        pick ->> 'model_name',
        pick ->> 'ticker',
        pick ->> 'direction',
        (pick ->> 'rank')::int,
        (pick ->> 'confidence')::numeric,
        (pick ->> 'expected_return_pct')::numeric,
        pick ->> 'reasoning',
        'pending'
    FROM jsonb_array_elements(p_picks) AS pick;
END;
$$;

REVOKE ALL ON FUNCTION public.replace_daily_stock_picks(UUID, JSONB) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.replace_daily_stock_picks(UUID, JSONB) TO service_role;

COMMENT ON FUNCTION public.replace_daily_stock_picks(UUID, JSONB)
    IS 'Atomically replaces all picks of a daily stock basket (force-rerun safe).';
