---
tags: [source, web, tanstack-query, patterns]
category: source
source: docs/web/TANSTACK_BEST_PRACTICES.md
---

# Source: TanStack Query Best Practices

Centralized query patterns and conventions for the web app.

Key details:

- **Query Options Factory**: All queries at `src/lib/queries.ts` using `queryOptions` / `infiniteQueryOptions` with named parameters for type safety
- **Hybrid fetching**: Server loaders for initial page load (SEO) + `useSuspenseQuery` for client-side caching
- **Cursor pagination**: `pageSize + 1` pattern for large datasets, `useInfiniteQuery`
- **SSR-safe QueryClient**: Server creates new client per request, browser uses singleton with smart retry (no retry on 404s)
- **Default staleTime**: 1 minute; Today page auto-refreshes on configurable interval during market hours
- **Mutations**: Use `useMutation` directly (no wrappers), invalidate cache on success
