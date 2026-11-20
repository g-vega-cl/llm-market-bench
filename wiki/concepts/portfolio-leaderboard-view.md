---
tags: [web, leaderboard, charts, ui, portfolio]
category: concept
---

# Portfolio Leaderboard View

The recipe desk homepage renders the public portfolio leaderboard as **one lane per portfolio** — every ranked row carries its own sparkline — instead of overlaying all series in a single shared chart frame. `TopPortfolios` (`apps/web/src/features/home/pages/TopPortfolios.tsx`) owns the rendering; the geometry helpers live in `apps/web/src/features/home/lib/chart-geometry.ts` (`ChartBox`, `chartDomain`, `polylinePoints`, `valueToY`).

## Why One Lane Per Portfolio

Five equity lines in one frame cross inside a few pixels and become unreadable. Giving each series its own row — while sharing a single y-scale — keeps the comparison honest (a taller wiggle still means a bigger return) without the spaghetti overlay.

## The Underlying View

`public.portfolio_leaderboard` is defined by
`supabase/migrations/20261119120000_portfolio_leaderboard_exclude_archived.sql`
(`CREATE OR REPLACE VIEW ... WITH (security_invoker = true)`). Its CTE chain is
`excluded → bounds → windowed → anchored → ranked`, and it projects
`window_start`, `window_days` (`30`), and `median_return_pct` alongside the
ranked rows. The view comment states the contract: *"Public homepage ranking:
every live portfolio by return from its window-start anchor (30 days, min 5
observations, flat series excluded, archived/superseded owners excluded before
ranking). median_return_pct is the median of that population."*

## Ranking Population

`bounds` fixes `window_start = CURRENT_DATE - INTERVAL '30 days'`. `windowed`
keeps `portfolio_performance` rows at or after that date; `anchored` groups per
portfolio and picks the anchor as the **last observation before** `window_start`
(via `LEFT JOIN LATERAL`), falling back to the first in-window observation when
no prior row exists. `ranked` then keeps only portfolios that satisfy every one
of:

- `observations >= 5`
- `anchor_equity > 0`
- `last_equity <> anchor_equity` — a flat series has no return to rank
- `last_date >= (SELECT MAX(date) FROM public.portfolio_performance) - 3` — a
  portfolio that stopped reporting cannot hold a rank; three sessions of slack
  covers a gap
- `p.owner_id NOT IN (SELECT owner_id FROM excluded)`

`return_pct` is `ROUND(((last_equity / NULLIF(anchor_equity, 0)) - 1) * 100, 4)`
and `rank` is `RANK() OVER (ORDER BY (last_equity / NULLIF(anchor_equity, 0)) DESC, portfolio_id)`.

## Excluded Owners

The board ranks live portfolios only. `excluded(owner_id)` in
`supabase/migrations/20261119120000_portfolio_leaderboard_exclude_archived.sql`
lists every owner id declared in `packages/config/models.json`
(`ARCHIVED_PORTFOLIO_OWNER_IDS`) plus three owners whose model was replaced and
that have not traded since (`gpt-5.6-luna`, `MiniMax-M3`, `deepseek-v4-flash`).

The declared group covers `sys-daily-spy-MiniMax-M3`,
`sys-daily-spy-close-MiniMax-M3`, `sys-daily-spy-deepseek-v4-flash`,
`sys-daily-spy-close-deepseek-v4-flash`,
`sys-daily-tlt-close-deepseek-v4-flash`, `sys-daily-tlt-close-gpt-5.6-luna`,
`sys-daily-spy-close-jev-local-autoresearched`, and
`sys-daily-spy-close-jev-four-regime-champion`. The superseded group is not
declared archived, so the engine still marks them to market; they are
"outdated" rather than retired, and only the board needs to say so.

The exclusion is applied inside `ranked`, before `RANK()`, so one population feeds
the rank column, the median, the worst row and the count. `trackedCount` is a
`count: 'exact'` read of this view, which means "portfolios being ranked", not
"portfolios that exist".

The series views join this view and inherit the exclusion; no separate filter.

A retired portfolio is a record, not a competitor: before this filter the board
ranked eight committed-archived system portfolios at ranks 3, 5, 6, 7, 17, 19 and
24, and GPT 5.6 Luna appeared twice — once as `sys-daily-tlt-close-gpt-5.6-luna`
and once as the bare model owner.

`apps/engine/tests/test_archived_portfolios.py::test_leaderboard_excludes_every_declared_archived_owner`
scrapes every `*portfolio_leaderboard*.sql` migration for the `excluded(owner_id)`
CTE and fails when `models.json` declares an owner the view still ranks, so the
two readers of that declaration cannot drift again.

Never add a current model owner to that array. `gpt-6-luna` replaced
`gpt-5.6-luna` and the two ids share a prefix, so retiring the version must not
retire the model: `test_board_never_excludes_a_current_model_owner` intersects the
array with every `*_MODEL` value in `models.json` and fails if any of them appears.

Luna 6 is absent from the board today for an unrelated reason — it has two sessions
of history and the view requires five observations — not because of the exclusion
list.

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

`apps/engine/tests/test_archived_portfolios.py` pins the config/view parity of the archived-owner exclusion (see above).

## Related

- [[entities/web-app]] — TanStack Start dashboard that hosts the desk
- [[concepts/recipe-public-stats]] — the public desk payload feeding this view
- [[concepts/zero-frontend-compute]] — leaderboard data is materialised server-side
- [[concepts/deploy-skew-payload-tolerance]] — payload normalization across the loader boundary
- [[entities/database]] — hosts the `portfolio_leaderboard` view and its migrations
