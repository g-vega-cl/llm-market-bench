---
tags: [web, leaderboard, charts, ui, portfolio]
category: concept
---

# Portfolio Leaderboard View

The recipe desk homepage renders the public portfolio leaderboard as **one lane per portfolio** — every ranked row carries its own sparkline — instead of overlaying all series in a single shared chart frame. `TopPortfolios` (`apps/web/src/features/home/pages/TopPortfolios.tsx`) owns the rendering; the geometry helpers live in `apps/web/src/features/home/lib/chart-geometry.ts` (`ChartBox`, `chartDomain`, `polylinePoints`, `valueToY`).

## Why One Lane Per Portfolio

Five equity lines in one frame cross inside a few pixels and become unreadable. Giving each series its own row — while sharing a single y-scale — keeps the comparison honest (a taller wiggle still means a bigger return) without the spaghetti overlay.

## Data Contract

`TopPortfoliosProps`:

```ts
interface TopPortfoliosProps {
    rows: LeaderboardRow[];
    medianReturnPct?: number | null;
    worst?: LeaderboardRow | null;
    spy?: EquityPoint[];
    trackedCount: number | null;
    windowDays: number;
    degraded?: boolean;
    starterNames?: string[];
}
```

`LeaderboardRow` is `{ portfolioId, label, returnPct, observations, series: EquityPoint[] }` and `EquityPoint` is `{ date, value }`.

## Shared Y-Scale

The domain is computed once from every series on the board — `rows`, the optional `worst` row, and the SPY benchmark — via `chartDomain(seriesList)`, then passed to every `Spark`. The zero baseline is drawn as a dashed `stroke-voxel-bevel-hi` line at `valueToY(0, SPARK, domain)`.

## Spark

`SPARK = { width: 144, height: 34, padding: 4 }`. Each sparkline is an inline `<svg>` with `role="img"` and a `<title>` of the form `"<label>, <n> sessions"` for screen readers. The series polyline uses `strokeWidth={2}` with round joins/caps; an empty series renders the baseline only.

## Row Layout

A row is a `voxel-trough` `<li>`: a fixed-width mono rank column, a truncating bold label, the sparkline, and the return coloured by `returnClass` (`null` → `text-voxel-muted`, `>= 0` → `text-success`, else `text-danger`).

## Worst Row

When `worst` is supplied it is published beneath the winners behind a `border-t-2 border-voxel-bevel-hi` divider, labelled `Lowest of {trackedCount}` (or `Lowest on the board` when the count is null), ranked with `trackedCount` (or `—`), and drawn with `stroke-danger`.

## SPY Benchmark Row

When `spy.length > 0` the benchmark gets its own row: rank `—`, suffix `(benchmark)`, `stroke-voxel-muted` line, and `returnPct` taken from the last SPY point.

## Caption And Summary

The `figcaption` reads `"{windowDays} days from each portfolio's window open · one shared scale · the dashed line is zero."` The summary paragraph beside the lanes reads `"{trackedCount} portfolios on the {windowDays}-day board"` (or the count-less variant), appends `· median {formatPct(medianReturnPct)}` when a median is present, and closes with `": the return each carried from the window open, and the loser at the bottom of it."`

## Degraded And Empty States

- `degraded` → `"The portfolio board is unavailable right now — the desk below is unaffected."`
- `rows.length === 0` → `"The portfolio board fills after the next close."`

## Loader-Boundary Normalization

`normalizeLeaderboard` in `apps/web/src/routes/index.tsx` coerces the new `worst` row through `normalizeRows([raw.worst])[0] ?? null` so its nested `series` array survives the server-fn boundary — the same deploy-skew crash class as `4be16417`.

## Tests

`TopPortfolios.test.tsx` pins: one lane per portfolio (no six-line overlay), the loser published under the winners, the dashed muted benchmark polyline, per-sparkline screen-reader titles, the board median beside the count, and the empty state.

## Related

- [[entities/web-app]] — TanStack Start dashboard that hosts the desk
- [[concepts/recipe-public-stats]] — the public desk payload feeding this view
- [[concepts/zero-frontend-compute]] — leaderboard data is materialised server-side
- [[concepts/deploy-skew-payload-tolerance]] — payload normalization across the loader boundary
