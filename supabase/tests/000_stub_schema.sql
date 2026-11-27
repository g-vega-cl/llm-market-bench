-- Minimal schema the token migration expects, for the SQL contract harness.
-- Mirrors only the columns the migration and its RPCs touch.

CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.strategy_recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL DEFAULT gen_random_uuid(),
    name TEXT NOT NULL DEFAULT 'stub',
    is_live BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    turbo_expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.recipe_execution_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES public.strategy_recipes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL DEFAULT gen_random_uuid(),
    mode TEXT NOT NULL DEFAULT 'backtest',
    status TEXT NOT NULL DEFAULT 'pending',
    heartbeat_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.recipe_user_quotas (
    user_id UUID PRIMARY KEY,
    max_live_recipes INTEGER NOT NULL DEFAULT 1,
    daily_backtest_limit INTEGER NOT NULL DEFAULT 2
);
