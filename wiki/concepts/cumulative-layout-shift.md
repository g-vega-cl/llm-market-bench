---
tags: [ui, ux, layout, performance, design-system]
category: concept
---

# Cumulative Layout Shift (CLS) Prevention

Cumulative Layout Shift (CLS) measures visual stability by tracking unexpected layout shifts during a page's lifecycle. In financial and analytical dashboards like Benchify, layout stability is critical: traders and analysts rapidly scan timeframes, macro indicators, and model decisions. A sudden layout jump—caused by a skeleton collapsing, a slow query unmounting a table, or a network reconnect refetching data—disorients user attention and risks accidental clicks.

Benchify enforces a strict zero-layout-shift standard across all data loading and transition lifecycles.

## The Anti-Pattern: Skeleton Shimmers

Skeleton loaders (`CardSkeleton`, pulsing gray wireframe rectangles) are a common web pattern that actively harms dashboard usability:

1. **Height Mismatch Whiplash**: Skeletons are static approximations (e.g., 4 rows of 64px). Real data might return 0 rows, 1 row, or 20 rows. When real data resolves, the container abruptly snaps to its true height, shoving all downstream content down or pulling it up.
2. **Double Render Jitter**: The user first perceives pulsing gray cards, and then within 50–200ms the entire screen flickers and replaces them with colored cards and typography.
3. **Destructive Refetches**: In naive implementations, initiating a background revalidation or changing an active tab replaces the existing rendered content with skeletons, erasing working context while the request is in flight.

## Core Architectural Invariants

Benchify mandates five design and querying rules to eliminate layout shifts:

### 1. Zero Skeletons & Silent Suspense Fallbacks

Pulsing placeholder skeletons are strictly eliminated across web pages (e.g., [`apps/web/src/features/today/pages/TodayPage.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/today/pages/TodayPage.tsx)).

Instead of rendering artificial skeletons, components wrapped in React `<Suspense>` use silent fallbacks:

```tsx
{/* Silent Suspense: no pulsing skeletons or layout displacement */}
<Suspense fallback={null}>
    <AgentInsights memories={data.memories} />
</Suspense>
```

When coupled with server-side rendering (SSR) and prefetching, the initial markup renders immediately with server-hydrated state.

### 2. Stale-While-Revalidate with `keepPreviousData`

When toggling timeframes (e.g., 7D, 30D, All-Time in [`apps/web/src/features/leaderboard/pages/LeaderboardPage.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/leaderboard/pages/LeaderboardPage.tsx)), the user expects uninterrupted visibility of the current table.

Using TanStack Query's `placeholderData: keepPreviousData` ensures the current dataset remains rendered while the new timeframe fetches in the background:

```tsx
const { data, isLoading } = useQuery({
    queryKey: ['leaderboard', timeframe],
    queryFn: () => fetchLeaderboard(timeframe),
    placeholderData: keepPreviousData,
});

// Table never unmounts during timeframe transitions; 
// full-page loader only shows on cold starts when zero models exist
{isLoading && models.length === 0 ? (
    <LoadingSpinner />
) : (
    <LeaderboardTable models={models} />
)}
```

### 3. Resilient In-Memory Fallbacks on Network Disconnect

Network interruptions, offline states, or server database timeouts must never wipe out hydrated client views:

- Server fetch functions (e.g. [`apps/web/src/features/today/api/fetch-today-data.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/today/api/fetch-today-data.ts), [`apps/web/src/features/concepts/api/fetch-concepts.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/concepts/api/fetch-concepts.ts), [`apps/web/src/features/home/api/fetch-barometer.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/home/api/fetch-barometer.ts)) retain their last valid in-memory payload (`cachedTodayData`, `cachedConcepts`, `cachedMarketFeeling`).
- If an upstream query fails, the function returns the cached state rather than returning an empty array (`[]`) or `null`.
- On cold starts with no cache available, functions throw an error so TanStack Query retries via exponential backoff rather than treating network failure as an empty database.

### 4. Exponential Backoff & Jitter

Configured in [`apps/web/src/lib/query-client.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/lib/query-client.tsx):

- Retries use exponential backoff with full randomized jitter ($1000 \times 2^{\text{attempt}} + \text{rand}(0, 500)\text{ms}$, capped at 10s).
- Non-retriable client errors (`400`, `401`, `403`, `404`) are skipped immediately to prevent retry thrashing.
- On reconnection, TanStack Query's `onlineManager` automatically triggers background revalidation without clearing the display.

### 5. Intrinsic Grid & Container Sizing

Fluid layout rules prevent cards from shifting horizontally or wrapping unexpectedly when adjacent cards hydrate:

- Combine CSS Grid with `repeat(auto-fit, minmax(min(100%, 15rem), 1fr))` so column boundaries are established intrinsically by parent container width rather than by asynchronous children.
- Use `min-w-0` on flex items and `min-h-[...]` baselines on multi-card sections to stabilize the vertical rhythm.

## Related

- [[entities/design-system]] — UI primitive library, theme conventions, and layout governance
- [[concepts/fluent-responsive-design]] — Breakpoint-free intrinsic responsive layouts
- [[concepts/zero-frontend-compute]] — Keeping the presentation layer clean of heavy client math
