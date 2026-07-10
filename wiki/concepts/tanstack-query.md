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

## Related

- [[entities/web-app]]
- [[sources/web-query-patterns-source]]
