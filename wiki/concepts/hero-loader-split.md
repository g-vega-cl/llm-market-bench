---
tags: [web, performance, tanstack, loader, lcp, parallelism]
category: concept
---

# Hero Loader Split

A pattern for keeping TanStack Start route loaders fast: split the homepage (or any LCP-critical route) into two parallel server functions, where the **hero loader** is a single Supabase query and the **full loader** streams in below it under `<Suspense>` boundaries.

## Why

The homepage `MarketStatusHero` block is the LCP element. It only needs the latest `market_feeling` row and the current ET date. Meanwhile the rest of the page wants 9 parallel Supabase queries: newsletters, trades, decisions, memories, future events, macro cache, 5000-row price history, and macro stats. Running them all inside a single `loader` serializes the critical paint on the slowest query (the `price_history` pull), and the LCP element can't paint until everything is ready.

The split pattern solves this by:

1. Running both loaders in parallel via `Promise.all([getHero(), getFull()])` in the route's `loader`.
2. The hero loader returns after a single `market_feeling` query (plus cheap ET date math), so the hero can paint first.
3. The full loader streams in independently. Its `useSuspenseQuery` in the page body has a 60 s in-memory cache, so warm function instances pay nothing.
4. The hero data is passed as a prop to `TodayPage`, which spreads it into `MarketStatusHero`'s `data` prop. The rest of the page renders below the hero with its own `<Suspense>` fallback skeleton.

## Implementation

### Hero loader: `fetchTodayHeroData`

Lives in `apps/web/src/features/today/api/fetch-today-hero-data.ts`. Single Supabase query, 60 s in-memory cache keyed on the ET date string.

```ts
export interface TodayHeroData {
    marketFeeling: (MarketFeeling & { formattedTime: string }) | null;
    isMarketOpen: boolean;
    isSentimentStale: boolean;
    todayDateString: string;
}

let cache: CacheEntry | null = null;
const CACHE_TTL_MS = 60 * 1000;

export async function fetchTodayHeroData(): Promise<TodayHeroData> {
    const now = new Date();
    const estDateStr = now.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
    if (cache && cache.estDateStr === estDateStr && Date.now() - cache.fetchedAt < CACHE_TTL_MS) {
        return cache.data;
    }
    // ... single market_feeling query + ET date math
    cache = { estDateStr, fetchedAt: Date.now(), data };
    return data;
}

export function __resetHeroCacheForTests(): void { cache = null; }
```

### Server functions wired in parallel

In `apps/web/src/routes/index.tsx`:

```ts
const getTodayData = createServerFn({ method: 'GET' }).handler(async () => fetchTodayData());
const getTodayHeroData = createServerFn({ method: 'GET' }).handler(async () => fetchTodayHeroData());

export const Route = createFileRoute('/')({
    loader: async () => {
        const [hero, data] = await Promise.all([getTodayHeroData(), getTodayData()]);
        return { hero, data };
    },
    component: RouteComponent,
});
```

The `Promise.all` means both loaders start at the same instant; the hero resolves first and `MarketStatusHero` paints while the full loader is still running.

### `TodayPage` consumes both

`TodayPage` now takes both a `hero` prop and an `initialData` prop:

```ts
<MarketStatusHero data={{ ...data, marketFeeling: hero.marketFeeling, ... }} />
<Suspense fallback={<div className="animate-pulse … h-32" />}>
    <GlobalMacroStats macroStats={data.macroStats} />
</Suspense>
```

The hero is rendered with data from the small loader. The macro stats and other modules are wrapped in `<Suspense>` boundaries so they stream in.

### TanStack Query integration

A new `todayQueries.hero()` key is added to `apps/web/src/features/today/queries/options.ts` with a 30 s `staleTime` so the hero can be re-fetched quickly without spamming Supabase.

## When to apply

Use the hero loader split when:

- A page has one LCP-critical block (hero, summary card, table-of-contents) that depends on minimal data
- The rest of the page depends on a fan-out of slow queries (multiple tables, large historical ranges, aggregations)
- TTFB or LCP is failing the Lighthouse ≥0.90 budget

Don't bother when:

- The whole page depends on a single query that already returns in <100 ms
- The hero block and the rest of the page are different routes (use route-level `loader` for each instead)

## TDD Coverage

`apps/web/src/features/today/api/fetch-today-hero-data.test.ts` (4 cases):
- Returns expected shape on a single `market_feeling` query
- 60 s warm in-memory cache returns the cached data on a second call
- Cache resets across ET date boundaries
- Test-only `__resetHeroCacheForTests()` clears the cache between cases

`apps/web/src/features/today/api/fetch-today-data.test.ts` (3 new cases):
- `consolidates price_history queries into a single RPC call (no raw 5000-row query)`
- `returns a warm in-memory cache hit on the second call within 60s (zero Supabase calls)`
- `does not load reasoning logs and does not return them in TodayData payload`

## Related

- [[entities/web-app]] — Dashboard where this pattern is applied
- [[entities/macro-tracker]] — server-side `latest_per_ticker_per_day` RPC that complements the hero split
- [[concepts/performance-auditing-strategy]] — Performance budget and parallel loader guidance
- [[concepts/posthog-stealth-proxy]] — lazy PostHog init that lives below the hero, not above it
