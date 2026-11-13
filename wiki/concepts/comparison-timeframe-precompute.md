---
tags: [web, portfolios, performance, caching, tanstack-start, zero-frontend-compute]
category: concept
---

# Comparison Payload Cache & Timeframe Precompute

The `/portfolios` comparison chart needs the full equity history of every active portfolio plus every benchmark series. Fetching that per timeframe toggle, or per navigation, produced a visible loading placeholder and repeated database round-trips for identical data. The page now resolves the comparison payload **once** behind a 4-hour server cache and precomputes all four timeframe slices during render, so switching between `7D` / `30D` / `90D` / `ALL` is an O(1) map lookup with no refetch and no layout jump.

## Server-side payload cache (`fetchCachedComparisonData`)

`apps/web/src/features/portfolios/api/fetch-portfolios.ts` exports:

- `ComparisonPayload` — `{ portfolios, startDate, endDate, benchmarkData }`, the single shape consumed by both the route loader and the page.
- `COMPARISON_CACHE_TTL_MS` — `4 * 60 * 60 * 1000`.
- `clearComparisonPayloadCache()` — test/ops hook that drops both the cached payloads and the in-flight map.
- `fetchCachedComparisonData(benchmarks, maxDays = 36500)` — the cached entry point.

The function composes `fetchAllActivePortfolioPerformance(maxDays)` and `fetchBenchmarkHistory(benchmarks, startDate, endDate)` and layers three guarantees on top:

1. **Cache key** — the benchmark tickers are sorted and joined, then suffixed with `maxDays` (`SPY,QQQ:36500`). Two callers requesting the same benchmark set in a different order share one cache entry.
2. **In-flight deduplication** — a concurrent call for a key that is already fetching returns the *existing* promise (`inFlightComparisonRequests`) instead of issuing a second set of queries. The entry is removed in a `finally` block.
3. **Last-known-good fallback** — a fetch that throws returns the cached payload when one exists (even if it is past the TTL) and only rethrows when there is nothing to serve. A transient database timeout therefore degrades to stale-but-usable history rather than an empty chart.

Within the TTL the cached object is returned by reference — consumers must treat the payload as immutable, which is why consumers only ever read it.

### Client-side alignment

`portfolioQueries.comparison` (`apps/web/src/features/portfolios/queries/options.ts`) sets `staleTime` and `gcTime` to 4 hours, matching the server TTL so the browser does not refetch a payload the loader just handed down and the cache entry survives a full session of timeframe switching.

### Route loader

`apps/web/src/routes/portfolios/index.tsx` builds the loader data from a parallel pair — `getPortfolios()` and `getComparisonData()` in a `Promise.all` — and returns `{ portfolios, comparisonData }`. The route component forwards `comparisonData` as `initialComparisonData` and tolerates the legacy array-shaped loader payload (`Array.isArray(loaderData)`) so an in-flight deploy cannot break the page.

`PortfoliosPage` seeds the comparison query with `initialData: initialComparisonData`, so the chart mounts on the first render of the hydrated HTML — the `Loading performance comparison…` placeholder never appears on a normal navigation.

## Timeframe precompute (`comparison-timeframes.ts`)

`apps/web/src/features/portfolios/lib/comparison-timeframes.ts` owns the series math and is pure (no React, no I/O):

| Export | Purpose |
| :--- | :--- |
| `ComparisonTimeframe` | `'7d' \| '30d' \| '90d' \| 'all'` |
| `COMPARISON_TIMEFRAMES` | The ordered tuple driving the timeframe buttons and the precompute map |
| `computeTimeframeSlice(comparisonData, tf, now?)` | Filters, rebases, and ranks one timeframe |
| `precomputeAllTimeframes(comparisonData, now?)` | Returns `Record<ComparisonTimeframe, TimeframeSlice>` for all four |

`PortfoliosPage` memoises `precomputeAllTimeframes(comparisonData)` and indexes it by the active timeframe, so a timeframe click causes a re-render only — never a fetch and never a recompute of the other three slices.

### Cutoff derivation

- `'all'` uses the sentinel cutoff `0000-01-01`, so no reference date is needed at all.
- The other windows subtract 7 / 30 / 90 days in UTC from a **reference date** that defaults to `comparisonData.endDate` (parsed as `T00:00:00Z`) rather than `new Date()`. Deriving the cutoff from the payload makes the slice deterministic for a given payload, which keeps server-rendered and hydrated output identical (see [[concepts/rendering-strategies]]).

Filtering compares `YYYY-MM-DD` strings (`p.date >= cutoffDateStr`) instead of constructing `Date` objects per row, avoiding timezone drift and per-row allocation.

### Rebase and ranking

For each portfolio the slice keeps the rows inside the window, takes the **first** row's `totalEquity` as the baseline, and emits `value = (totalEquity - firstEquity) / firstEquity * 100` (0 when the baseline is non-positive). Portfolios with no rows in the window emit an empty `performance` array. Slices are then sorted by the last point's value descending, tie-broken by `ownerId`, so the leader of the selected window is always first — this is what makes the chart's identity ordering flip between windows (a portfolio up 20% over 7D can lead while a different portfolio leads over `ALL`).

Benchmark series are filtered by the same cutoff, so the benchmark line can never extend past the portfolio window.

## Render-phase `latestData`

`PortfolioComparisonChart` now derives `latestData` with `React.useMemo(() => getLatestData(), [getLatestData])` instead of mirroring it into state inside a `useEffect`. The value is correct on the very first render (no post-commit correction frame), so the chip percentages in [[entities/portfolio-comparison-selector]] never render a stale value for one frame and the equal-sized chip grid never resizes.

## Tests

- `apps/web/src/features/portfolios/api/fetch-portfolios.test.ts` — TTL hit returns the same object reference without re-querying `portfolios`, and an expired-TTL fetch failure returns the previous payload.
- `apps/web/src/features/portfolios/lib/comparison-timeframes.test.ts` — empty-payload slices, 7D vs ALL leader inversion, cutoff derived from `endDate` when `now` is omitted.
- `apps/web/src/features/portfolios/pages/PortfoliosPage.test.tsx` — the chart mounts from `initialComparisonData` with no loading placeholder, and a `7D` click renders the 7-day leader without a refetch.
- `apps/web/src/features/portfolios/components/PortfolioComparisonSelector.test.tsx` — chip grid classes, truncation, and zero `dark:` utility escapes.

## Related

- [[entities/portfolio-comparison-selector]] — the selector and chart that consume these slices
- [[entities/web-app]] — the `/portfolios` route and its loader
- [[concepts/tanstack-query]] — `initialData`, `staleTime`/`gcTime`, and settlement gating
- [[concepts/rendering-strategies]] — hydration-safe deterministic derivation
- [[concepts/zero-frontend-compute]] — payload shaping stays server-side; the client only slices pre-fetched series
- [[concepts/cumulative-layout-shift]] — why timeframe switches must not remount or resize the chart
