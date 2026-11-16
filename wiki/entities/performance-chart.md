---
tags: [web, portfolios, ui, chart, d3]
category: entity
---

# Performance Chart

A D3-based line/area chart in `apps/web/src/features/portfolios/components/PerformanceChart.tsx` that renders a single portfolio's performance series alongside an optional benchmark (e.g. SPY). It is the single-portfolio counterpart to the multi-agent [[entities/portfolio-comparison-selector]] chart.

## Rendering

- Draws the portfolio series as a monotone-X line (`#0ea5e9`) plus a gradient-filled area beneath it.
- When a `selectedBenchmark` is supplied and `benchmarkData[selectedBenchmark]` exists, an amber (`#f59e0b`) benchmark line is overlaid.
- All paths are clipped to the plot area via a `<clipPath id="performance-chart-clip">` rect sized to the SVG `width`/`height`, so lines never bleed past the chart bounds.

## Benchmark bounding

The benchmark series is strictly filtered to the active portfolio date range before rendering:

- The min/max dates are computed from the portfolio's parsed data (`d3.extent`).
- Benchmark points outside `[minTime, maxTime]` are dropped, so a benchmark whose raw history predates the portfolio's first data point (common in 90D/All timeframes) does not extend the line beyond the visible window.
- The same `clip-path` is applied to the benchmark path as an additional guard.

## Props

| Prop | Type | Purpose |
| :--- | :--- | :--- |
| `data` | `PerformanceSnapshot[]` | The portfolio's equity history series. |
| `benchmarkData` | `Record<string, BenchmarkDataPoint[]>` (optional) | Benchmark history keyed by ticker. |
| `selectedBenchmark` | `string` (optional) | The **settled** benchmark ticker to overlay. Only set once its history has actually resolved. |
| `pendingBenchmark` | `string` (optional) | Ticker currently being fetched. Renders an in-flow `Loading <TICKER>...` status in the header. |
| `benchmarkError` | `string` (optional) | Error message to surface in-flow (e.g. `Failed to load GLD`). |
| `showPercentage` | `boolean` (default `false`) | Switches the title to `Performance vs Benchmark` and normalizes the series to percentage returns. |

## In-flow benchmark status (no floating overlays)

The chart header is a wrap-safe row (`flex flex-wrap items-center justify-between gap-2 min-w-0`) whose right-hand status slot renders exactly one of three mutually exclusive states, each as a `whitespace-nowrap` span inside a `flex flex-wrap items-center gap-2 min-w-0` group:

1. **Loading** — `Loading {pendingBenchmark}...` in muted `text-zinc-400` while a newly selected benchmark's history is in flight.
2. **Error** — `{benchmarkError}` in `text-red-500` when the benchmark fetch failed.
3. **Normalized hint** — `Normalized to percentage returns` when a benchmark is settled and `showPercentage` is active.

This keeps benchmark feedback in-flow per the design system's zero-floating-tooltip rule (see [[concepts/in-flow-inspection]]) and prevents the header from wrapping awkwardly at narrow widths (see [[concepts/fluent-responsive-design]]).

## Non-suspending benchmark switching

`PerformanceChart` is a pure presentational consumer: it never fetches. The `selectedBenchmark` / `pendingBenchmark` / `benchmarkError` triple is produced by `usePortfolioBenchmark` (`apps/web/src/features/portfolios/hooks/usePortfolioBenchmark.ts`), which uses a non-suspending `useQuery` with `enabled: Boolean(selectedBenchmark && hasDateRange)` and `placeholderData: keepPreviousData`.

Because the hook derives `status` (`'idle' | 'loading' | 'settled' | 'error'`) and `settledBenchmark` directly from `benchmarkQuery.data` / `benchmarkQuery.isPlaceholderData` — with no `useEffect` state synchronization — switching benchmarks never suspends the page up to the route `<Suspense>` boundary. The previously settled benchmark line stays mounted while the new one loads, and the chart only swaps `selectedBenchmark` once the new series has real points. An empty `{}` response settles cleanly with no mislabeled benchmark, and a rejected fetch surfaces `benchmarkError` instead of hanging on the loading state.

Consumers: `PortfolioDetailPage` (`/portfolios/:id`) and `RenkoAgentPageView` (`/renko`). See [[concepts/tanstack-query]] for the full hook semantics and the `keepPreviousData` rationale.

## Tests

- `apps/web/src/features/portfolios/components/PerformanceChart.test.tsx` — asserts the in-flow `Loading QQQ...` status renders with `whitespace-nowrap` inside a `flex-wrap` / `min-w-0` header, and that `benchmarkError` renders as a `whitespace-nowrap` error span.
- `apps/web/src/features/portfolios/pages/PortfolioDetailPageBenchmark.test.tsx` — asserts the page and chart stay mounted (no Suspense fallback) across `None → SPY → QQQ → None` transitions, that the previous settled benchmark remains rendered while the next one loads, that switching back to `None` issues zero extra fetches, and that empty `{}` responses and rejected fetches clear the loading state without hanging.

## Related

- [[entities/portfolio-comparison-selector]] — multi-agent comparison chart with the same benchmark-bounding pattern
- [[entities/web-app]] — the `/portfolios/:id` and `/renko` routes that host this chart
- [[concepts/tanstack-query]] — `usePortfolioBenchmark`, `keepPreviousData`, and non-suspending on-demand overlays
- [[concepts/in-flow-inspection]] — why benchmark status renders in-flow rather than as a floating tooltip
- [[concepts/fluent-responsive-design]] — wrap-safe header layout rules
- [[concepts/zero-frontend-compute]]
