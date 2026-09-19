---
tags: [supabase, postgrest, security, grants, data-api]
category: concept
---

# Supabase Grant Convention

Starting October 30, 2026, Supabase stops auto-granting `public` schema table
access to the Data API roles (`anon`, `authenticated`, `service_role`). Every
table in `public` must have explicit `GRANT` statements to be accessible via
PostgREST, supabase-js, or GraphQL.

## Background

Historically, Supabase automatically granted `SELECT`, `INSERT`, `UPDATE`,
`DELETE` on all `public` schema tables to the `anon`, `authenticated`, and
`service_role` roles. This allowed tables to be used immediately with the
Data API without explicit grants.

Supabase is removing this implicit behavior:
- **New projects**: May 30, 2026
- **Existing projects** (like llm-market-bench): October 30, 2026

Without explicit grants, PostgREST returns a `42501` error with the exact
`GRANT` statement needed to fix it.

## Convention for This Project

Every migration that creates a table in `public` MUST include explicit grants.
Use this template:

```sql
CREATE TABLE IF NOT EXISTS public.your_table (
    ...
);

-- Enable RLS
ALTER TABLE public.your_table ENABLE ROW LEVEL SECURITY;

-- Policies (define row-level access)
CREATE POLICY "Allow public read" ON public.your_table
    FOR SELECT USING (true);

CREATE POLICY "Allow service_role full access" ON public.your_table
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- REQUIRED: Explicit grants for Data API access
GRANT SELECT ON public.your_table TO anon, authenticated;
GRANT ALL ON public.your_table TO service_role;
```

## Access Patterns

This project has two consumers of the Data API:

| Consumer | Role | Key | Needs |
|---|---|---|---|
| Engine | `service_role` | `SUPABASE_SERVICE_ROLE_KEY` | ALL (CRUD) |
| Web frontend | `anon` / `authenticated` | `SUPABASE_ANON_KEY` | SELECT only |

**Rule**: Grant `SELECT` to `anon, authenticated` on any table with a public
read RLS policy. Grant `ALL` to `service_role` on every table (engine needs
full access).

For tables that should NOT be publicly readable, grant only to `service_role`. Note that `newsletter_snapshots` originally had only a `service_role` policy but was updated to allow `SELECT` for `anon` and `authenticated` to support the Today page's Daily Intelligence Briefing.

## Existing Tables

A one-time migration (`20260513000000_add_explicit_grants_for_data_api.sql`)
backfills explicit grants for all 18 existing tables. This migration is
idempotent — `GRANT` statements are safe to re-run.

## Automated Enforcement

This convention is strictly enforced via CI and the pre-commit hook. The test `apps/engine/tests/test_migration_grants.py` automatically scans all migration files and enforces four critical security invariants:
1. **Per-file explicit grants (`test_new_tables_have_grants`)**: Every migration created after the cutoff date must define explicit `GRANT` statements for `service_role` and public roles (`anon, authenticated`).
2. **Global RLS coverage (`test_all_active_tables_have_rls`)**: Every active table in the public schema must have `ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;`.
3. **Policy coverage (`test_all_active_tables_have_policies`)**: Every active table with RLS must define explicit access policies (`CREATE POLICY`).
4. **Per-file RLS enforcement (`test_new_tables_have_rls_enabled_in_file`)**: Any new migration creating a table must enable RLS directly within the same migration file.

### Incident History: `options_data_cache` (September 2026)
Migration `20260901000000_create_options_data_cache.sql` included explicit `GRANT` statements but omitted RLS activation. Supabase's Security Advisor triggered an `rls_disabled_in_public` critical alert on 2026-09-13. The issue was resolved in `20260919150000_enable_rls_on_options_data_cache.sql`, and static analysis in `test_migration_grants.py` was extended to permanently prevent table creation without RLS.


## Verification

After applying grants, verify a table is accessible:

```sql
-- Check current grants on a table
SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_name = 'your_table';
```

Or test via PostgREST:

```sh
curl "https://<project>.supabase.co/rest/v1/your_table?limit=1" \
  -H "apikey: <anon_key>"
```

## Related

- [[entities/database]]
- [[entities/engine]]
- [[entities/web-app]]
