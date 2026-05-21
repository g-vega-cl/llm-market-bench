-- Migration: Add explicit GRANTs for Supabase Data API access
-- Description: Proactively adds explicit GRANT statements to all tables in the public schema.
-- Context: Supabase is phasing out automatic table exposure to the Data API (PostgREST).
--   New projects: May 30, 2026  |  Existing projects: October 30, 2026
--   Without explicit GRANTs, PostgREST returns 42501 "permission denied" errors.
-- See: https://supabase.com/docs/guides/database/api#granting-access-to-tables

-- ────────────────────────────────────────────────────────────────────
-- TABLES WITH PUBLIC READ ACCESS (web frontend reads via anon key)
-- GRANT SELECT to anon + authenticated (matching existing RLS policies)
-- ────────────────────────────────────────────────────────────────────

GRANT SELECT ON public.market_data_cache TO anon, authenticated;
GRANT SELECT ON public.portfolios TO anon, authenticated;
GRANT SELECT ON public.portfolio_positions TO anon, authenticated;
GRANT SELECT ON public.portfolio_performance TO anon, authenticated;
GRANT SELECT ON public.trades TO anon, authenticated;
GRANT SELECT ON public.price_history TO anon, authenticated;
GRANT SELECT ON public.concept_metrics TO anon, authenticated;
GRANT SELECT ON public.memories TO anon, authenticated;
GRANT SELECT ON public.decisions TO anon, authenticated;
GRANT SELECT ON public.ingestion_logs TO anon, authenticated;
GRANT SELECT ON public.system_audits TO anon, authenticated;
GRANT SELECT ON public.llm_reasoning_logs TO anon, authenticated;
GRANT SELECT ON public.cause_and_effect TO anon, authenticated;
GRANT SELECT ON public.market_feeling TO anon, authenticated;
GRANT SELECT ON public.correlation_runs TO anon, authenticated;
GRANT SELECT ON public.correlation_data TO anon, authenticated;
GRANT SELECT ON public.prompt_experiments TO anon, authenticated;

-- ────────────────────────────────────────────────────────────────────
-- SERVICE ROLE FULL ACCESS (engine uses service_role key for all writes)
-- GRANT ALL to service_role on every table
-- ────────────────────────────────────────────────────────────────────

GRANT ALL ON public.newsletter_snapshots TO service_role;
GRANT ALL ON public.memories TO service_role;
GRANT ALL ON public.decisions TO service_role;
GRANT ALL ON public.concept_metrics TO service_role;
GRANT ALL ON public.market_data_cache TO service_role;
GRANT ALL ON public.portfolios TO service_role;
GRANT ALL ON public.portfolio_positions TO service_role;
GRANT ALL ON public.portfolio_performance TO service_role;
GRANT ALL ON public.trades TO service_role;
GRANT ALL ON public.price_history TO service_role;
GRANT ALL ON public.ingestion_logs TO service_role;
GRANT ALL ON public.system_audits TO service_role;
GRANT ALL ON public.llm_reasoning_logs TO service_role;
GRANT ALL ON public.cause_and_effect TO service_role;
GRANT ALL ON public.market_feeling TO service_role;
GRANT ALL ON public.correlation_runs TO service_role;
GRANT ALL ON public.correlation_data TO service_role;
GRANT ALL ON public.prompt_experiments TO service_role;
