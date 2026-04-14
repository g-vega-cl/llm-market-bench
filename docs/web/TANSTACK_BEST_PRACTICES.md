# TanStack Query & Start Best Practices Guide

## Overview

This guide documents the TanStack Query and TanStack Start best practices implemented in the Benchify project.

## ✅ Implemented Best Practices

### 1. QueryClient Setup (SSR-Safe)

**File:** [`src/lib/query-client.tsx`](../src/lib/query-client.tsx)

```typescript
import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60, // 1 minute
        retry: (failureCount, error) => {
          if (error instanceof Error && error.message.includes('404')) {
            return false
          }
          return failureCount < 3
        },
        throwOnError: false,
        gcTime: 1000 * 60 * 5, // 5 minutes
      },
      mutations: {
        retry: 1,
        throwOnError: false,
      },
    },
    queryCache: new QueryCache({
      onError: (error, query) => {
        console.error('[QueryCache] Error:', error, 'Query:', query.queryKey)
      },
    }),
    mutationCache: new MutationCache({
      onError: (error, variables, context, mutation) => {
        console.error('[MutationCache] Error:', error)
      },
    }),
  })
}

// Singleton pattern for browser
let browserQueryClient: QueryClient | undefined = undefined

function getQueryClient() {
  if (typeof window === 'undefined') {
    return makeQueryClient() // Server: new client each time
  }
  if (!browserQueryClient) browserQueryClient = makeQueryClient()
  return browserQueryClient // Browser: singleton
}
```

**Why:**
- ✅ Prevents state leakage between SSR requests
- ✅ Singleton pattern in browser for cache consistency
- ✅ Smart retry logic (no retry on 404s)
- ✅ Global error logging
- ✅ DevTools guarded in production

---

### 2. Query Options Factory (Centralized)

**File:** [`src/lib/queries.ts`](../src/lib/queries.ts)

```typescript
import { queryOptions, infiniteQueryOptions } from '@tanstack/react-query'
import { queryKeys } from './query-keys'

export const queries = {
  // Simple query with named parameters
  today: (opts?: { fetchFn?: () => Promise<any> }) =>
    queryOptions({
      queryKey: queryKeys.today.data(),
      queryFn: opts?.fetchFn,
      staleTime: 1000 * 60 * 2,
    }),
  
  // Detail query with required id
  portfolios: {
    detail: (opts: { id: string; fetchFn?: () => Promise<any> }) =>
      queryOptions({
        queryKey: queryKeys.portfolios.detail(opts.id),
        queryFn: opts.fetchFn,
        staleTime: 1000 * 60 * 5,
      }),
  },
  
  // Benchmark history query (for portfolio comparison)
  benchmarks: {
    history: (opts: { tickers: string[]; startDate: string; endDate: string; fetchFn?: () => Promise<any> }) =>
      queryOptions({
        queryKey: queryKeys.benchmarks.history(opts.tickers, opts.startDate, opts.endDate),
        queryFn: opts.fetchFn,
        staleTime: 1000 * 60 * 5,
      }),
  },
  
  // Infinite query with cursor pagination
  reasoning: {
    list: (opts?: { cursor?: string; fetchFn?: (cursor: string | undefined) => Promise<any> }) =>
      infiniteQueryOptions({
        queryKey: queryKeys.reasoning.list(opts?.cursor),
        queryFn: ({ pageParam }) => opts?.fetchFn ? opts.fetchFn(pageParam) : Promise.reject('fetchFn required'),
        initialPageParam: undefined,
        getNextPageParam: (lastPage: any) => lastPage?.nextCursor ?? undefined,
        staleTime: 1000 * 60 * 5,
      }),
  },
}
```

**Why:**
- ✅ Single source of truth for query configuration
- ✅ Type-safe query options with named parameters
- ✅ Consistent stale times and keys across SSR and CSR
- ✅ Built-in support for TanStack Start server functions
- ✅ Clear, explicit API at call sites
- ✅ Easy to extend with optional parameters

---

### 3. Infinite Query Pattern (Centralized)

**File:** [`src/lib/queries.ts`](../src/lib/queries.ts)

```typescript
export const queries = {
  memories: {
    list: (opts?: { 
      filters?: { status?: string; memoryType?: string }; 
      cursor?: string; 
      fetchFn?: (cursor: string | undefined) => Promise<any> 
    }) =>
      infiniteQueryOptions({
        queryKey: queryKeys.memories.list(opts?.filters),
        queryFn: ({ pageParam }) => opts?.fetchFn ? opts.fetchFn(pageParam) : Promise.reject('fetchFn required'),
        initialPageParam: undefined,
        getNextPageParam: (lastPage: any) => lastPage?.nextCursor ?? undefined,
        staleTime: 1000 * 60 * 5,
      }),
  },
}
```

**Why:**
- ✅ Simplifies component code
- ✅ Centralizes pagination logic
- ✅ Consistent behavior for all infinite lists
- ✅ Named parameters make usage explicit and type-safe

---

### 3. Cursor-Based Pagination

**File:** [`src/routes/reasoning/-queries.ts`](../src/routes/reasoning/-queries.ts)

```typescript
const PAGE_SIZE = 50

export async function fetchReasoningLogs(
  cursor?: string, 
  pageSize: number = PAGE_SIZE
): Promise<PaginatedReasoningLogs> {
  let query = supabase
    .from('llm_reasoning_logs')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(pageSize + 1) // Fetch one extra to check if there's more

  if (cursor) {
    query = query.lt('created_at', cursor)
  }

  const { data, error } = await query
  
  const hasMore = data.length > pageSize
  const paginatedData = hasMore ? data.slice(0, pageSize) : data
  const nextCursor = hasMore && paginatedData.length > 0
    ? paginatedData[paginatedData.length - 1].created_at
    : null

  return { data: paginatedData, hasMore, nextCursor }
}
```

**Why:**
- ✅ Better than offset pagination for real-time data
- ✅ Prevents duplicate/missing items
- ✅ More efficient database queries
- ✅ Consistent performance at any depth

---

### 4. Infinite Query Pattern

**File:** [`src/routes/reasoning/index.tsx`](../src/routes/reasoning/index.tsx)

```typescript
const {
  data,
  fetchNextPage,
  hasNextPage,
  isFetching,
  isFetchingNextPage,
  status,
  error
} = useInfiniteQuery({
  ...queries.reasoning.list({ 
    cursor: undefined, 
    fetchFn: (pageParam) => getReasoningLogsFn({ data: pageParam }) 
  }),
  initialPageParam: undefined as string | undefined,
  getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
  staleTime: 1000 * 60 * 5, // 5 minutes
})

// Flatten all pages
const allLogs = React.useMemo(
  () => data?.pages.flatMap(page => page.data) || [],
  [data]
)
```

**Why:**
- ✅ Fast initial load
- ✅ Progressive loading
- ✅ Automatic caching
- ✅ Built-in loading states
- ✅ **Simplified implementation using `infiniteQueryOptions`**
- ✅ **Named parameters for explicit, type-safe API usage**

---

### 5. Suspense Query Pattern

**File:** [`src/routes/index.tsx`](../src/routes/index.tsx)

```typescript
import { useSuspenseQuery } from '@tanstack/react-query'
import { queries } from '~/lib/queries'

function TodayPage() {
  const initialData = Route.useLoaderData()
  const getTodayDataFn = useServerFn(getTodayData)

  const { data } = useSuspenseQuery({
    ...queries.today({ fetchFn: () => getTodayDataFn() }),
    initialData,
  })

  // ...
}
```

**Why:**
- ✅ Simplifies component logic (no more `isLoading` checks)
- ✅ Better integration with TanStack Start SSR
- ✅ Declarative data fetching
- ✅ Automatic loading states via Suspense boundaries
- ✅ Named parameters make API usage explicit

---

### 5. Load More UI Pattern

```tsx
{hasNextPage && (
  <button
    onClick={() => fetchNextPage()}
    disabled={isFetchingNextPage}
  >
    {isFetchingNextPage ? 'Loading...' : 'Load More'}
  </button>
)}

{!hasNextPage && allLogs?.length > 0 && (
  <div>• End of reasoning traces •</div>
)}
```

**Why:**
- ✅ User-controlled loading
- ✅ Prevents accidental data loading
- ✅ Clear visual feedback
- ✅ Better accessibility

---

### 6. Error Boundaries (No External Dependencies)

**File:** [`src/components/ui/QueryErrorBoundary.tsx`](../src/components/ui/QueryErrorBoundary.tsx)

```typescript
import * as React from 'react'

class ErrorBoundaryClass extends React.Component {
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} resetErrorBoundary={this.reset} />
    }
    return this.props.children
  }
}

export function QueryErrorBoundary({ children }) {
  return <ErrorBoundaryClass>{children}</ErrorBoundaryClass>
}
```

**Usage:**
```tsx
<QueryErrorBoundary>
  <YourComponent />
</QueryErrorBoundary>
```

**Why:**
- ✅ Graceful error handling
- ✅ Prevents app crashes
- ✅ User-friendly error messages
- ✅ Auto-retry capability
- ✅ **Zero dependencies** - Uses React's built-in APIs

---

### 7. Proper Mutation Pattern

**Direct import from TanStack Query:**

```typescript
import { useMutation } from '@tanstack/react-query'

const loginMutation = useMutation({
  mutationFn: loginFn,
  onSuccess: async (data) => {
    if (!data?.error) {
      await router.invalidate()
      router.navigate({ to: '/' })
    }
  },
})
```

**Why:**
- ✅ Automatic loading/error states
- ✅ Cache invalidation support
- ✅ Optimistic updates support
- ✅ Proper TypeScript types
- ✅ **No unnecessary wrappers** - Use TanStack's hook directly

---

### 8. DevTools in Development Only

```typescript
{process.env.NODE_ENV === 'development' && (
  <ReactQueryDevtools initialIsOpen={false} />
)}
```

**Why:**
- ✅ Smaller production bundle
- ✅ No dev UI in production
- ✅ Better security

---

### 9. Query API Reference (Named Parameters)

**All queries now use named parameters for clarity and type safety:**

```typescript
// Simple queries (optional fetchFn)
queries.today({ fetchFn })
queries.concepts.list({ fetchFn })
queries.causeAndEffect.list({ fetchFn })
queries.portfolios.list({ fetchFn })

// Detail queries (required id + optional fetchFn)
queries.portfolios.detail({ id, fetchFn })
queries.portfolios.positions({ id, fetchFn })
queries.portfolios.trades({ id, fetchFn })
queries.portfolios.performance({ id, fetchFn })
queries.memories.detail({ id, fetchFn })
queries.reasoning.detail({ id, fetchFn })

// Infinite queries (optional cursor, filters, fetchFn)
queries.memories.list({ filters, cursor, fetchFn })
queries.reasoning.list({ cursor, fetchFn })
```

**Example Usage:**

```typescript
// Today page
const { data } = useSuspenseQuery({
  ...queries.today({ fetchFn: () => getTodayDataFn() }),
  initialData,
})

// Portfolio detail
const { data } = useSuspenseQuery({
  ...queries.portfolios.detail({ 
    id: portfolioId, 
    fetchFn: () => getPortfolioDataFn(portfolioId) 
  }),
  initialData,
})

// Infinite list (memories)
const { data, fetchNextPage } = useInfiniteQuery({
  ...queries.memories.list({ 
    filters: { status: 'active' }, 
    fetchFn: (pageParam) => getMemoriesFn({ data: pageParam }) 
  }),
})

// Infinite list (reasoning)
const { data, fetchNextPage } = useInfiniteQuery({
  ...queries.reasoning.list({ 
    cursor: undefined, 
    fetchFn: (pageParam) => getReasoningLogsFn({ data: pageParam }) 
  }),
})
```

**Benefits:**
- ✅ **Explicit API** - Each parameter is clearly labeled at call sites
- ✅ **Type Safety** - TypeScript enforces required params and types
- ✅ **Extensibility** - Easy to add optional params without breaking changes
- ✅ **Consistency** - All queries follow the same pattern
- ✅ **Better DX** - IDE autocomplete works perfectly with named params

---

## 📋 Checklist for New Features

When adding new data fetching to your components:

### For List Pages
- [ ] Use cursor-based pagination if list can grow
- [ ] Set PAGE_SIZE = 50 (or appropriate size)
- [ ] Return `{ data, hasMore, nextCursor }`
- [ ] Use `useInfiniteQuery` hook
- [ ] Add "Load More" button
- [ ] Handle loading and error states
- [ ] Use `queries.<resource>.list({ filters, cursor, fetchFn })` pattern

### For Detail Pages
- [ ] Use server-side loader if data is small
- [ ] Use `useQuery` if client-side fetching needed
- [ ] Add proper query keys using `queries` factory with named parameters
- [ ] Use `queries.<resource>.detail({ id, fetchFn })` pattern
- [ ] Set appropriate `staleTime`

### For Simple Queries
- [ ] Use `queries.<resource>({ fetchFn })` pattern
- [ ] Set appropriate `staleTime` based on data volatility

### For Mutations
- [ ] Use `useMutation` hook
- [ ] Add `onSuccess` for cache invalidation
- [ ] Add `onError` for user notifications
- [ ] Consider optimistic updates for better UX

### Error Handling
- [ ] Wrap components in `QueryErrorBoundary`
- [ ] Show user-friendly error messages
- [ ] Log errors for debugging
- [ ] Provide retry mechanism

---

## 📊 Performance Guidelines

### Query Configuration

| Scenario | staleTime | gcTime | retry |
|----------|-----------|--------|-------|
| Real-time data | 0 | 1 min | 3 |
| Dashboard data | 1 min | 5 min | 3 |
| Static config | 10 min | 30 min | 1 |
| User preferences | Infinity | Infinity | 1 |

### Pagination

| Data Size | Pattern | Page Size |
|-----------|---------|-----------|
| < 100 items | Fetch all | N/A |
| 100-1000 items | Cursor pagination | 50 |
| > 1000 items | Cursor pagination | 100 |
| Infinite scroll | Virtual scroll | 20 |

---

## 🔧 Common Patterns

### Invalidate and Refetch

```typescript
const queryClient = useQueryClient()

const deleteMutation = useMutation({
  mutationFn: deleteItem,
  onSuccess: () => {
    // Invalidate and refetch
    queryClient.invalidateQueries({ queryKey: queryKeys.items.all })
  },
})
```

### Optimistic Update

```typescript
const updateMutation = useMutation({
  mutationFn: updateItem,
  onMutate: async (newData) => {
    await queryClient.cancelQueries({ queryKey: queryKeys.items.list() })
    
    const previous = queryClient.getQueryData(queryKeys.items.list())
    
    queryClient.setQueryData(queryKeys.items.list(), (old) => [...old, newData])
    
    return { previous }
  },
  onError: (err, variables, context) => {
    queryClient.setQueryData(queryKeys.items.list(), context.previous)
  },
})
```

### Prefetching

```typescript
// In loader
await queryClient.prefetchQuery({
  queryKey: queryKeys.items.detail(id),
  queryFn: () => fetchItem(id),
  staleTime: 1000 * 60,
})
```

---

## 📚 Additional Resources

- [TanStack Query Documentation](https://tanstack.com/query/latest/docs/framework/react/overview)
- [TanStack Start Documentation](https://tanstack.com/start/latest/docs/framework/react/overview)
- [Query Key Factories Guide](https://tanstack.com/query/latest/docs/framework/react/guides/query-keys)
- [Infinite Queries Guide](https://tanstack.com/query/latest/docs/framework/react/guides/infinite-query)
- [Reasoning Page Optimization](./reasoning-page-optimization.md)

---

## 🎯 Next Steps (Future Improvements)

### Phase 2 (Completed)
- [x] Add `useSuspenseQuery` for simpler loading states
- [x] Implement query prefetching for related routes
- [x] Add `queryOptions` for type-safe query configuration

### Phase 3 (Medium Priority)
- [ ] Add retry with exponential backoff
- [ ] Add optimistic updates for all mutations
- [ ] Implement query invalidation strategies
- [ ] Add performance monitoring
- [ ] Consider virtual scrolling for very large lists
