-- ============================================================================
-- Migration: 20261119030000_revoke_anon_read_on_recipe_builder_usage.sql
-- Description: PostgREST's default privileges let `anon`/`authenticated` hold
--              table SELECT on new public tables. Row Level Security then filters
--              every row, so the API answered 200 with `[]` instead of 403 —
--              no data leaked, but the table was advertised on the public API
--              surface. Revoke the grant so the endpoint returns 401/403.
-- ============================================================================

REVOKE ALL ON public.recipe_builder_usage FROM anon, authenticated;

COMMENT ON TABLE public.recipe_builder_usage IS
    'Per-user daily /build compile spend. Service-role only: no anon/authenticated grants.';
