# TanStack Query Best Practices

## Query Options Factory

All queries are defined centrally in `src/lib/queries.ts` using `queryOptions` / `infiniteQueryOptions`. Call sites use named parameters for type safety:

```typescript
// Simple query
queries.today({ fetchFn: () => getTodayDataFn() })

// Detail query (required id)
queries.portfolios.detail({ id: portfolioId, fetchFn: () => getPortfolioFn(portfolioId) })

// Infinite query (cursor pagination)
queries.reasoning.list({ cursor: undefined, fetchFn: (pageParam) => getReasoningFn({ data: pageParam }) })
```

**Named parameters** make the API explicit at call sites, enable IDE autocomplete, and allow easy addition of optional params without breaking changes.

## Data Fetching Strategy

Hybrid pattern: server loaders for fast initial page load (SEO) + `useSuspenseQuery` for client-side caching and background refetching.

## Route Configurations

staleTime values are configured per route in `src/lib/queries.ts`. The Today page auto-refreshes on a configurable interval during market hours.

## Cursor-Based Pagination

Used for large datasets (above the configured cursor pagination threshold). Fetches `pageSize + 1` to determine if more data exists:

```typescript
// Returns { data, nextCursor, hasMore }
const { data, fetchNextPage, hasNextPage } = useInfiniteQuery({
  ...queries.reasoning.list({ cursor: undefined, fetchFn }),
})
```

## QueryClient Setup (SSR-Safe)

Server creates a new QueryClient per request. Browser uses a singleton with smart retry (no retry on 404s) and global error logging. Default `staleTime`: 1 min.

## Checklist for New Data Fetching

- Use `queries.<resource>.(list|detail)({ params })` pattern
- Cursor pagination for lists that can grow
- Wrap in `QueryErrorBoundary` (zero-dependency, React class component)
- Handle loading, error, and empty states
- Set appropriate `staleTime` based on data volatility
- For mutations: use `useMutation` directly (no wrappers), invalidate cache on success

## Key Files

- `src/lib/queries.ts` — Centralized query options
- `src/lib/query-keys.ts` — Type-safe key factories
- `src/lib/query-client.tsx` — SSR-safe QueryClient
- `src/components/ui/QueryErrorBoundary.tsx` — Error boundary
