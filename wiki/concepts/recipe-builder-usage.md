---
tags: [recipes, rate-limiting, builder, database, security]
category: concept
---

# Recipe Builder Usage

`public.recipe_builder_usage` enforces a per-user daily cap on `/build` compiles, which spend real proxy tokens. The table is keyed on `(user_id, usage_day)` with a `compiles` counter and `updated_at`.

## Atomic Spend

`consume_builder_compile(p_user UUID)` atomically increments the day's counter and returns the running total, so two concurrent requests can never both slip under the cap:

```sql
INSERT INTO public.recipe_builder_usage (user_id, usage_day, compiles)
VALUES (p_user, (NOW() AT TIME ZONE 'utc')::date, 1)
ON CONFLICT (user_id, usage_day)
DO UPDATE SET compiles = public.recipe_builder_usage.compiles + 1,
              updated_at = NOW()
RETURNING compiles INTO new_count;
```

The function is `SECURITY DEFINER`, revoked from `PUBLIC`/`anon`/`authenticated`, and granted only to `service_role`.

## No Public API Surface

PostgREST's default privileges let `anon`/`authenticated` hold table SELECT on new public tables. RLS then filters every row, so the API answered `200 []` instead of `403` — no data leaked, but the table was advertised on the public API surface. A follow-up migration revokes all grants from `anon`/`authenticated` so the endpoint returns `401/403`. The table is service-role only.

## Related

- [[concepts/recipe-public-stats]] — the public board tables
- [[concepts/rls-enforcement-standard]] — row-level security conventions
- [[concepts/supabase-grant-convention]] — grant/revoke conventions
- [[entities/recipe-studio]] — the recipe builder UI
