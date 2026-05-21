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
  - **Cleanup (2026-05-21)**: A duplicate centralized factory (`apps/web/src/lib/queries.ts` and `apps/web/src/lib/query-keys.ts`) was audited, identified as dead code, and deleted to preserve codebase cleanliness.

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

## Related

- [[entities/web-app]]
- [[sources/web-query-patterns-source]]
