---
tags: [performance, database, supabase, pgvector, web, query-optimization]
category: concept
---

# Vector Egress Stripping & Explicit Column Projections

The web dashboard must never pull the pgvector `embedding` column (or other unused heavy columns) over the wire. Because `memories` and `decisions` rows carry a large vector `embedding` column used only for server-side semantic search, a naive `.select('*')` silently transfers megabytes of invisible vector data on every page load — inflating TTFB and wasting bandwidth with data the UI never renders. The fix is to replace wildcard selects with explicit scalar column projections, centralized in reusable constants.

## The Problem

Supabase/PostgREST `.select('*')` returns every column, including the `embedding` vector. On high-volume feeds (Today page, Cause & Effect page) this invisible egress is pure waste: the vector is never displayed, yet it dominates the payload size. The same applies to nested joins — `decisions(*)` inside a `trades` query drags the full decision row (and any heavy columns) into the response.

## The Solution: Named Projection Constants

Each feature defines a single source-of-truth constant for its column projection so the query shape is testable and consistent across call sites.

### `MEMORY_SCALAR_COLUMNS`

Defined in `apps/web/src/features/memories/api/fetch-memories.ts` and imported wherever `memories` rows are read (e.g. `fetch-today-data.ts`). Lists only the scalar columns the UI consumes (`id`, `content`, `created_at`, `status`, `importance_score`, `metadata`, …) and deliberately omits `embedding`.

### `DECISION_SCALAR_COLUMNS`

Defined in `apps/web/src/features/today/api/fetch-today-data.ts`:

```ts
export const DECISION_SCALAR_COLUMNS =
    'id, source_id, ticker, signal, confidence, reasoning, model_provider, model_name, created_at, price, status, trade_id, limit_price, metadata';
```

### `TRADES_TODAY_SELECT`

Composes the trades projection with a nested, explicitly-projected decision join instead of `decisions(*)`:

```ts
export const TRADES_TODAY_SELECT = `*, portfolios(owner_id), decisions(${DECISION_SCALAR_COLUMNS})`;
```

### `CAUSE_AND_EFFECT_SELECT`

Defined in `apps/web/src/features/cause-and-effect/api/fetch-cause-and-effect.ts`, projecting only the scalar fields of the joined event memory:

```ts
export const CAUSE_AND_EFFECT_SELECT = '*, event:memories(id, content, created_at)';
```

## Affected Call Sites

- `apps/web/src/features/today/api/fetch-today-data.ts` — `trades`, `decisions`, and both `memories` queries (recent feed and future-catalyst feed) now use the projection constants instead of `*`.
- `apps/web/src/features/cause-and-effect/api/fetch-cause-and-effect.ts` — both `fetchCauseAndEffect` and `fetchCauseAndEffectByEventId` use `CAUSE_AND_EFFECT_SELECT`.

## TDD Enforcement

The zero-load TDD suite asserts the projection invariants so a future refactor cannot silently reintroduce wildcard selects:

- `fetch-today-data.test.ts` spies on `.select()` per table and asserts `memories`/`decisions` calls are never `'*'`, never contain `embedding`, and do contain the expected scalar keys (`id`, `content`, `reasoning`); it also asserts the `trades` join never uses `decisions(*)` and equals `TRADES_TODAY_SELECT`.
- `fetch-cause-and-effect.test.ts` asserts the select argument never contains `event:memories(*)` and does contain `event:memories(id, content, created_at)` for both fetch functions.

## Related

- [[concepts/performance-auditing-strategy]] — TTFB reduction and excising unused high-volume queries
- [[concepts/zero-frontend-compute]] — keeping heavy work off the presentation layer
- [[concepts/rag-strategy]] — where the `embedding` column is actually consumed (server-side semantic search)
- [[entities/web-app]] — the dashboard consuming these projections
