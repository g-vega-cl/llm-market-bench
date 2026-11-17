-- Migration: market_feeling.model_used default follows the MiniMax slot rename
-- Created: 2026-11-17
--
-- `20260614191000_update_minimax_model_to_m3.sql` pinned the column default to
-- 'MiniMax-M3'. The MiniMax slot now runs MiniMax-M3.1-Flash
-- (packages/config/models.json), so any insert that omits model_used would stamp
-- a retired id into a table the home-page tape renders verbatim.
--
-- Historical rows keep the id they were actually written with: this only moves
-- the default forward.

ALTER TABLE public.market_feeling
    ALTER COLUMN model_used SET DEFAULT 'MiniMax-M3.1-Flash';
