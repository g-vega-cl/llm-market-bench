---
tags: [web, tanstack, query-options, typescript, architecture]
category: concept
---

# TanStack Query Patterns

The frontend application (`apps/web`) leverages **TanStack Query** (React Query) for state management, caching, background data refetching, and cursor-based pagination. Central to this integration is the **Query Options Factory** pattern, which ensures all queries are defined using type-safe named parameters.

## Architectural Architecture

To maintain high cohesion and follow a clean vertical feature-sliced monorepo structure, all query option factories and query keys are co-located directly inside their respective feature slices:

- **Feature-Specific Query Options & Keys**
  - Located inside each vertical feature slice at `apps/web/src/features/[feature]/queries/options.ts` and `keys.ts` (e.g., `portfolioQueries`, `reasoningQueries`, `todayQueries`).
  - These are the single source of truth for query definitions, imported and consumed by the frontend pages and components (e.g., `ReasoningPage.tsx` consumes `reasoningQueries.list`).
  - **Cleanup (2026-05-21)**: A duplicate centralized factory (`src/lib/queries.ts` and `src/lib/query-keys.ts` under `apps/web/`) was audited, identified as dead code, and deleted to preserve codebase cleanliness.

## Query Options Factory Pattern

Feature-specific query option factories strictly adhere to TanStack Query's recommended guidelines using `@tanstack/react-query` primitives:

### Type-Safe Named Parameters
Instead of passing loose arguments to fetch functions, all factories accept a single object containing named parameters (e.g., `{ id, fetchFn }`). This prevents argument-ordering bugs, enables clear IDE autocomplete, and permits frictionless extensions of optional query parameters:

```typescript
export const portfolioQueries = {
    detail: <T extends PortfolioDetailData>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: portfolioQueryKeys.detail(opts.id),
            queryFn: opts.fetchFn,
            staleTime: 1000 * 60 * 5,
        }),
};
```

### Cursor-Based Pagination Constraint
For infinite scroll queries (e.g., reasoning logs, audit logs, memories), the factory enforces type safety on the response structure. The generic type parameter `T` must extend a `CursorPage` definition, ensuring that the `getNextPageParam` callback can safely access `lastPage.nextCursor` at compile-time:

```typescript
type CursorPage = { nextCursor?: string | null };

export const reasoningQueries = {
    list: <T extends PaginatedReasoningLogs>(opts?: {
        cursor?: string;
        fetchFn?: (cursor: string | undefined) => Promise<T>;
    }) =>
        infiniteQueryOptions({
            queryKey: reasoningQueryKeys.list(opts?.cursor),
            queryFn: ({ pageParam }) =>
                opts?.fetchFn ? opts.fetchFn(pageParam) : Promise.reject(new Error('fetchFn required')),
            initialPageParam: undefined as string | undefined,
            getNextPageParam: (lastPage: T) => lastPage?.nextCursor ?? undefined,
            staleTime: 1000 * 60 * 5,
        }),
};
```

## SSR-Safe QueryClient Setup

To support server-side rendering (SSR) without leaking query data across concurrent user requests, `apps/web/src/lib/query-client.tsx` implements a singleton-safe pattern:

- **Server-Side**: A new `QueryClient` instance is instantiated per incoming request.
- **Browser-Side**: A single browser-wide `browserQueryClient` singleton is created and cached to avoid full cache resets on client route transitions.
- **Default Configurations**:
  - `staleTime` defaults to `1 minute` to avoid immediate client refetches after hydration.
  - Retries are capped at `3` with exponential backoff, skipping non-retriable failures like HTTP 404s.
  - Global `onError` logger hooks are configured on both the `QueryCache` and `MutationCache` to audit API failures seamlessly.

The client is wrapped around the root component in `apps/web/src/routes/__root.tsx` via the `QueryClientProviderWrapper`.

## Query Settlement Gating (`isQuerySettled`)

`apps/web/src/lib/query-client.tsx` exports `isQuerySettled(queries, isTransitionPending = false)`, the canonical predicate for deciding whether **secondary** UI affordances may render. It answers one question: *have all relevant queries and React transitions fully settled?*

```typescript
export interface QuerySettlementState {
    isFetched?: boolean;
    isFetching: boolean;
    isPending?: boolean;
    isSuccess?: boolean;
    isPlaceholderData?: boolean;
    data?: unknown;
}

export function isQuerySettled(
    queries: (QuerySettlementState | undefined | null)[] | QuerySettlementState | undefined | null,
    isTransitionPending = false,
): boolean;
```

### Semantics

- Accepts a single query result, an array of query results, or `null`/`undefined`.
- Returns `false` immediately when `isTransitionPending` is `true`.
- Returns `false` when the argument itself is `null`/`undefined`, or when any element of the list is `null`/`undefined`.
- Returns `true` for an empty list when no transition is pending.
- A query counts as settled only when it has valid data (`data !== undefined` and `isSuccess ?? true`) **and** is not `isFetching`, not `isPending`, and not `isPlaceholderData`.
- A hydrated query seeded from `initialData` (`isSuccess: true`, data present, not fetching) counts as settled even when `isFetched` is `false`.
- An errored query with no data (`isError: true`, `data: undefined`) is **not** settled.

### Usage pattern

Pages combine the helper with `useTransition` and pass the result down as an `isSettled` prop:

```tsx
const listQuery = useSuspenseQuery({ ...portfolioQueries.list({ fetchFn }), initialData });
const comparisonQuery = useQuery({
    ...portfolioQueries.comparison({ fetchFn: () => comparisonFetchFn() }),
    placeholderData: keepPreviousData,
});
const [isPending, startTransition] = React.useTransition();

const isQueriesSettled = isQuerySettled([listQuery, comparisonQuery]);
const isChartSettled = isQueriesSettled && !isPending;
```

Secondary elements gated on this flag include `Reset to Top 5` / `Reset Crosshair` buttons in `PortfolioComparisonChart` and volatile derived badges such as per-portfolio daily percentage moves on `PortfoliosPage`. Primary chart and container chrome stay stably mounted so gating never introduces layout shift — see [[concepts/cumulative-layout-shift]].

## Gotchas & Common Pitfalls

### Dynamic `initialData` Cache Pollution
Using React state as `initialData` in `useSuspenseQuery` or `useQuery` when the query key is dynamic (e.g., depends on a selected benchmark, filter, or page state) can cause cache pollution:
- **Pitfall**: When the state changes (e.g., the selected benchmark changes from `'SPY'` to `'QQQ'`), `useSuspenseQuery` is called with the new query key but the *old* `initialData` (which is still the data from `'SPY'`). React Query immediately seeds the cache for the new key (`'QQQ'`) with the old `'SPY'` data and marks it as fresh. When the fetch resolves and updates the `initialData` state variable, React Query ignores it because the cache entry is already marked as fresh and exists.
- **Solution**: Remove `initialData` entirely from `useSuspenseQuery` for dynamic-key queries. Add `placeholderData: keepPreviousData` so the **previous key's cached data** remains visible while the new key is fetching — preventing the Suspense boundary from firing and eliminating visual flicker. Wrap the state update in `React.useTransition` as an additional layer: the transition defers the state commit so React can keep rendering the old state until the new data is ready.

```typescript
import { keepPreviousData, useSuspenseQuery } from '@tanstack/react-query';

// Good: keepPreviousData keeps old data visible while new key loads.
const { data } = useSuspenseQuery({
    ...portfolioQueries.comparison({ benchmark: selectedBenchmark, fetchFn }),
    placeholderData: keepPreviousData, // ← prevents Suspense boundary flash
});

// In the event handler:
startTransition(() => setSelectedBenchmark(ticker)); // ← defers state update
```

### `key={dynamicValue}` on Expensive Components
Passing a dynamic value as the React `key` prop on a chart or data-heavy component forces a **full unmount + remount** every time the value changes — even if the component's own `useEffect`/memo dependencies would handle the update correctly:
- **Pitfall**: `<PortfolioComparisonChart key={selectedBenchmark} />` — changing the benchmark destroys the entire D3 SVG and all associated state, causing a jarring visual flash.
- **Solution**: Remove the `key` prop and let the component re-render naturally through its own dependency tracking (e.g., `useEffect([data, benchmarkData, selectedBenchmark])`). If a smooth animated transition is desired, add D3 transitions (opacity or path animations) rather than relying on React remounting.

```tsx
// Bad — unmounts the entire chart on every benchmark change:
<PortfolioComparisonChart key={selectedBenchmark} data={...} />

// Good — chart stays mounted and D3 re-draws in-place with a fade transition:
<PortfolioComparisonChart data={...} selectedBenchmark={selectedBenchmark} />
```

### Server Function Validation & Strict Error Types

With updated TanStack Start / Router packages:
- **Server Function Validation**: Deprecated `.inputValidator(...)` on `createServerFn` is superseded by `.validator(...)`. It accepts the same identity validator pattern `(d: T) => d` while avoiding Vite build-time deprecation warnings.
- **Strict Error Component Types**: Router `errorComponent` arguments strictly type `error` as `unknown` rather than ambient `any`. Error-checking logic must guard types explicitly (e.g., `error instanceof Error && error.message === '...'`) before accessing property fields.

## Related

- [[entities/web-app]]
- [[sources/web-query-patterns-source]]
- [[concepts/cumulative-layout-shift]]
- [[entities/portfolio-comparison-selector]]
