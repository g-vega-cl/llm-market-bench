---
tags: [web, portfolios, ui, chart, d3]
category: entity
---

# Performance Chart

A D3-based line/area chart in `apps/web/src/features/portfolios/components/PerformanceChart.tsx` that renders a single portfolio's performance series alongside an optional benchmark (e.g. SPY). It is the single-portfolio counterpart to the multi-agent [[entities/portfolio-comparison-selector]] chart, and it is shared by the portfolio detail page, the Renko agent page, and the recipe live-status page.

## Rendering

- Draws the portfolio series as a monotone-X line (`#0ea5e9`) plus a gradient-filled area beneath it.
- When a `selectedBenchmark` is supplied and `benchmarkData[selectedBenchmark]` exists, an amber (`#f59e0b`) benchmark line is overlaid.
- All paths are clipped to the plot area via a `<clipPath id="performance-chart-clip">` rect sized to the SVG `width`/`height`, so lines never bleed past the chart bounds.

## Benchmark bounding

The benchmark series is strictly filtered to the active portfolio date range before rendering:

- The window is derived from the portfolio's parsed data (`d3.extent`) and snapped to **UTC day boundaries**: `minTime` is `Date.UTC(y, m, d)` of the first portfolio date and `maxTime` is `Date.UTC(y, m, d, 23, 59, 59, 999)` of the last. A benchmark bar stamped anywhere inside the final trading day therefore stays inside the window instead of being dropped by a midnight-only cutoff.
- Benchmark points outside `[minTime, maxTime]` are dropped, so a benchmark whose raw history predates the portfolio's first data point (common in 90D/All timeframes) does not extend the line beyond the visible window.
- A surviving benchmark point whose timestamp is still earlier than `minDate` (a bar that landed inside the day window but before the portfolio's first print) is **aligned forward to `minDate`**, so the benchmark line starts exactly where the portfolio line starts rather than at a slightly earlier x position.
- The same `clip-path` is applied to the benchmark path as an additional guard.

### Headline readout alignment

The percentage readout above the chart resolves its benchmark point against the portfolio's **day range**, not a raw timestamp equality:

- `startDay` / `latestDay` are the `YYYY-MM-DD` prefixes of the first and last portfolio dates.
- The benchmark series is filtered to `p.date >= startDay && p.date <= latestDay` before lookup.
- The point is matched by exact `latestDate` first, then by `latestDay` (a benchmark bar stamped at midnight of the same calendar day), then falls back to the last point in the filtered window.

This keeps the reported portfolio-vs-benchmark change consistent with the drawn lines even when the two series carry different intraday timestamps.

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

The hook accepts an optional `initialBenchmark` (default `''`) that seeds the `selectedBenchmark` state, so a surface can open with a benchmark already selected — `RecipeLivePage` passes `'SPY'` so the live equity chart starts on the S&P 500 comparison instead of an empty overlay.

Because the hook derives `status` (`'idle' | 'loading' | 'settled' | 'error'`) and `settledBenchmark` directly from `benchmarkQuery.data` / `benchmarkQuery.isPlaceholderData` — with no `useEffect` state synchronization — switching benchmarks never suspends the page up to the route `<Suspense>` boundary. The previously settled benchmark line stays mounted while the new one loads, and the chart only swaps `selectedBenchmark` once the new series has real points. An empty `{}` response settles cleanly with no mislabeled benchmark, and a rejected fetch surfaces `benchmarkError` instead of hanging on the loading state.

Consumers: `PortfolioDetailPage` (`/portfolios/:id`), `RenkoAgentPageView` (`/renko`), and `RecipeLivePage` (`/recipes/live/$recipeId`). See [[concepts/tanstack-query]] for the full hook semantics and the `keepPreviousData` rationale.

## Shared benchmark server function (`getBenchmarkHistoryFn`)

`apps/web/src/features/portfolios/api/benchmark-server-fn.ts` exports `getBenchmarkHistoryFn`, the single `createServerFn({ method: 'GET' })` used by every benchmark overlay. It replaces the per-route `getBenchmarkData` server functions that `/portfolios/$portfolioId` and `/renko` each used to declare, and is re-exported from `apps/web/src/features/portfolios/index.ts`.

- **Ticker allowlist** — the requested tickers are filtered against `ALLOWED_BENCHMARK_TICKERS`, a `Set` built from `BENCHMARK_OPTIONS` in `BenchmarkSelector`, so the endpoint can only ever fetch a benchmark the selector can offer.
- **ISO date validation** — `startDate` and `endDate` must both match `^\d{4}-\d{2}-\d{2}$`.
- **Fail-soft** — an empty ticker list after filtering, or a malformed date, returns `{}` without touching the database; otherwise it delegates to `fetchBenchmarkHistory(tickers, startDate, endDate)`.

## Tests

- `apps/web/src/features/portfolios/components/PerformanceChart.test.tsx` — asserts the in-flow `Loading QQQ...` status renders with `whitespace-nowrap` inside a `flex-wrap` / `min-w-0` header, and that `benchmarkError` renders as a `whitespace-nowrap` error span.
- `apps/web/src/features/portfolios/pages/PortfolioDetailPageBenchmark.test.tsx` — asserts the page and chart stay mounted (no Suspense fallback) across `None → SPY → QQQ → None` transitions, that the previous settled benchmark remains rendered while the next one loads, that switching back to `None` issues zero extra fetches, and that empty `{}` responses and rejected fetches clear the loading state without hanging.
- `apps/web/src/features/recipes/pages/RecipeLivePage.test.tsx` — asserts the live equity chart defaults to SPY, switches to QQQ and back to `None`, and skips the benchmark fetch entirely for a single-day equity curve.

## Related

- [[entities/portfolio-comparison-selector]] — multi-agent comparison chart with the same benchmark-bounding pattern
- [[entities/recipe-live-status]] — the live recipe page that renders this chart over `paper_equity_curve`
- [[entities/web-app]] — the `/portfolios/:id`, `/renko`, and `/recipes/live/$recipeId` routes that host this chart
- [[concepts/tanstack-query]] — `usePortfolioBenchmark`, `initialBenchmark`, `keepPreviousData`, and non-suspending on-demand overlays
- [[concepts/in-flow-inspection]] — why benchmark status renders in-flow rather than as a floating tooltip
- [[concepts/fluent-responsive-design]] — wrap-safe header layout rules
- [[concepts/zero-frontend-compute]]
