-- ============================================================================
-- Migration: 20261113112000_drop_recipe_intraday_bars.sql
-- Description: Remove unused legacy DAG 5-minute bar cache table. Push v2
--              backtests read daily closing prices from public.price_history.
-- ============================================================================

DROP TABLE IF EXISTS public.recipe_intraday_bars;
