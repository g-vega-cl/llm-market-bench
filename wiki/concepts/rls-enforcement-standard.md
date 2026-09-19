---
tags: [supabase, security, rls, database, migrations]
category: concept
---

# RLS Enforcement Standard

Comprehensive Row-Level Security (RLS) enforcement standard requiring every active table in the public schema to have RLS enabled with explicit access policies, enforced via automated migration tests and CI.

## Core Requirements

Every migration creating a table must include:

1. **Explicit GRANT statements** — `GRANT SELECT, INSERT, UPDATE, DELETE ON public.<table> TO authenticated;` (and service_role where applicable)
2. **RLS enabled** — `ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;` in the same migration file
3. **Access policies** — At least one `CREATE POLICY` per table defining explicit access rules
4. **Per-file enforcement** — RLS activation must occur within the same migration file that creates the table

## Enforcement Layers

### Migration Test Suite

- **`test_new_tables_have_grants`** — Scans all migration SQL files after cutoff date `20260513`; any `CREATE TABLE` without explicit `GRANT` statements raises an assertion error
- **`test_all_active_tables_have_rls`** — Verifies every active table (created minus dropped) has RLS enabled
- **`test_all_active_tables_have_policies`** — Confirms every active table with RLS has at least one explicit policy
- **`test_new_tables_have_rls_enabled_in_file`** — Enforces RLS activation within the same migration file for tables created after the cutoff

### CI Integration

- Pre-commit hook runs the migration grant tests automatically
- Supabase Security Advisor alerts on `rls_disabled_in_public` critical findings
- Static analysis in `test_migration_grants.py` permanently prevents table creation without RLS

## Incident History

### `options_data_cache` (September 2026)

Migration `20260901000000_create_options_data_cache.sql` included explicit `GRANT` statements but omitted RLS activation. Supabase's Security Advisor triggered an `rls_disabled_in_public` critical alert on 2026-09-13. Resolved in `20260919150000_enable_rls_on_options_data_cache.sql`, which enables RLS and creates explicit read/full-access policies. The test suite was extended to permanently prevent this regression.

## Related

- [[concepts/supabase-grant-convention]] — Explicit GRANTs required for PostgREST Data API access
- [[entities/database]] — Supabase PostgreSQL schema with pgvector and RLS
- [[concepts/supabase-redirect-whitelisting]] — Supabase OAuth redirect whitelisting rules
