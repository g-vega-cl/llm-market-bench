---
tags: [data, postgres, homepage]
category: concept
---

# Portfolio Leaderboard View

`public.portfolio_leaderboard` is the public read model behind the homepage portfolio
spotlight and equity chart. Defined in
`supabase/migrations/20261119040000_portfolio_leaderboard_view.sql`.

## Shape

One row per tracked portfolio, ranked by trailing 30-day return:

| Column | Meaning |
| :--- | :--- |
| `portfolio_id` | FK to `portfolios.id` |
| `owner_id` | portfolio owner slug (`sys-*` for system strategies, model slug for LLM agents) |
| `first_date` / `last_date` | window bounds actually observed |
| `observations` | daily snapshots counted in the window |
| `anchor_date` | date of the snapshot the anchor came from |
| `anchor_equity` | equity at the window open (last snapshot before it, else the first in-window one) |
| `last_equity` | last observed equity |
| `return_pct` | `(last_equity / anchor_equity - 1) * 100`, rounded to 4dp |
| `rank` | `RANK()` over `return_pct` descending, `portfolio_id` breaking ties |
| `window_days` | the trailing window, 30 |
| `window_start` | the window boundary the SQL clock computed |
| `median_return_pct` | median `return_pct` of the same population |

## Filters

- `observations >= 5` — a two-snapshot portfolio cannot win on noise.
- `anchor_equity > 0` — a zero or negative anchor cannot produce a percentage return.
- `last_equity <> anchor_equity` — a flat 10,000 account is excluded so a
  portfolio that never traded cannot rank above a real loser.
- `last_date >= MAX(date) - 3` — a portfolio that stopped reporting cannot hold a
  rank; the chart would otherwise draw a line that silently stops mid-window.

Mechanical `sys-*` strategies compete on the same board as the LLM agents: the LLM
agent portfolios carried no trades at the time of writing, so excluding `sys-*`
would render an empty hero.

## Anchor, not first observation

Ranking and chart share one anchor: the last equity at or before the window
open, falling back to the first in-window snapshot for a portfolio younger than
30 days. Rebasing each series on its own first point hands a late starter a free
0% head start and makes two portfolios' returns incomparable.

The anchor is applied in SQL, not in the loader: `portfolio_leaderboard_series`
and `spy_benchmark_series` (below) already express every point as percent return
from the ranking anchor, so the web layer does no percentage arithmetic and the
chart cannot drift onto a different anchor than the ranking.

## Access

`GRANT SELECT` to `service_role` only, and the view is `security_invoker = true`,
so base-table RLS stays in force if the read role ever stops bypassing it. Keeping
the grant off `anon` means the numbers cannot be read straight from the public
PostgREST surface; the page still shows them.

## Web read path (`apps/web/src/features/home/api/portfolio-leaderboard.ts`)

`fetchPortfolioLeaderboard()` runs through `getDbAdminClient()` and returns a
`PortfolioLeaderboard`:

```ts
interface PortfolioLeaderboard {
    rows: LeaderboardRow[];      // top 5, each with a rebased series
    spy: EquityPoint[];          // dashed benchmark line
    medianReturnPct: number | null;
    trackedCount: number | null; // null when the count read failed
    windowDays: number;
    degraded: boolean;           // board unreadable — unknown, not empty
    spyUnavailable: boolean;     // portfolios loaded, benchmark did not
}
```

- **Ranked read** — `portfolio_leaderboard` ordered by `rank`, then `portfolio_id`,
  limited to `BOARD_SIZE = 5`, selecting `portfolio_id, owner_id, return_pct,
  observations, window_days, median_return_pct`. A read error throws `dbError(error)`,
  which keeps the PostgREST code (`PGRST205` stale schema cache vs `42P01` missing
  object need different responses; the message alone hides that).
- **Series read** — one `IN` query against `portfolio_leaderboard_series` for the
  five ids, ordered `date` ascending, mapping each row's pre-computed `return_pct`
  straight onto the row's `series`. No `rebaseToAnchor` step: the view already
  anchors every point on the same equity the ranking used. An unchecked error here
  would paint a blank chart that reads as "nothing traded yet", so it throws.
- **Benchmark read** — `spy_benchmark_series` ordered `date` ascending with
  `limit(SPY_MAX_ROWS = 120)`, mapping `return_pct` directly. The view already
  anchors SPY on the board's earliest `anchor_date` and keeps one row per session
  (last price of the day wins), so the loader does no rebasing and no date
  truncation. A benchmark failure returns `[]` and sets `spyUnavailable` without
  failing the board.
- **Count read** — `select('portfolio_id', { count: 'exact', head: true })`. It never
  falls back to the page length, which would report "1 portfolios" as fact; a failed
  count yields `trackedCount: null`.
- **Empty board** — `emptyLeaderboard(degraded = false)` returns a fresh object each
  call, so a caller mutating `rows` cannot poison the next render.
- **Labels** — `portfolioLabel(owner_id)` in `../lib/portfolio-label.ts` strips the
  `sys-` prefix, drops a `~operator/` namespace and a `-latest` marker, splits on
  `-`, `_`, and `/`, and keeps a small acronym set (`SPY`, `TLT`, `QQQ`, `VIX`, `ETF`,
  `AI`, `GPT`, `LLM`, `CPI`, `FED`, `SMA`, `USD`, …) uppercase.

### Route-boundary normalization

`normalizeLeaderboard(value)` in `apps/web/src/routes/index.tsx` coerces the loader
payload before it reaches the page, because each row carries a **nested** `series`
array that also crosses the loader boundary (coercing only the outer arrays was the
deploy-skew crash of `4be16417`). `normalizeRows` / `normalizePoints` drop malformed
points, non-numeric returns become `0`, a non-finite `trackedCount` becomes `null`, a
non-finite `windowDays` becomes `30`, and an **absent** payload sets `degraded: true`
— an unknown board is not a young one.

The homepage loader (`getHome`) fetches the desk and the board in parallel; a board
failure is logged and degrades to `emptyLeaderboard(true)` so the front door still
renders the desk.

## Chart geometry & rendering

`apps/web/src/features/home/lib/chart-geometry.ts` is pure and library-free:

- `chartDomain(seriesList)` — shared y/x domain across every series, always including
  zero so gains and losses read against one baseline, padded by `PAD_RATIO = 0.15`
  (a flat series is padded instead of collapsing to a zero-height line), with a
  `{ min: -1, max: 1, start: 0, end: 1 }` fallback for empty input.
- `polylinePoints(points, box, domain)` — SVG `points` string inside the box, dropping
  points with a non-finite value or unparseable date.
- `valueToY(value, box, domain)` — used for the dashed zero baseline.
- `lastPointXY(points, box, domain)` — the last plottable point's `{ x, y }`, used to
  place each line's endpoint marker and rank label; returns `null` when no point is
  plottable.

`EquityChart.tsx` renders that geometry as a server-rendered inline SVG
(`BOX = { width: 640, height: 160, padding: 12 }`) with `role="img"` and an
accessible label, one polyline per portfolio (first series thicker) plus a dashed
`stroke-voxel-muted` SPY line, a `figcaption` legend of literal `stroke-*`/`bg-*`
class pairs (a runtime `stroke-` → `bg-` swap produces a class Tailwind never
generates), and the axis caption `SPY dashed · <start> to <end> · scale …`. Each
plotted line carries a numbered endpoint marker (`lastPointXY` → a `circle` plus a
`fill-voxel-ink` rank `text`), and the legend prefixes each label with its rank
(`1. Max Pain`), so a series can be identified without relying on colour alone
(WCAG 1.4.1). Series with a single observation are skipped; when nothing is
plottable it renders `Equity curves appear after the first close.` No chart library,
no hover tooltips (design spec §10).

`TopPortfolios.tsx` renders the ranked five with `formatPct` returns, the
`trackedCount`/`windowDays` sentence, the starter-recipe chips, and the
`See all portfolios` / `Need inspiration?` links; an empty board renders either
`The portfolio board is unavailable right now — the desk below is unaffected.`
(`degraded`) or `The portfolio board fills after the next close.`

`HomeHero.tsx` hosts the idea form and the chart card, and prints the **board**
median (`leaderboard.medianReturnPct`) — not the recipe-desk median, which stays on
the desk header alongside the live and beat-SPY counts.

## Companion series views

`20261119060000_portfolio_leaderboard_series_views.sql` adds two read models so the
web layer does no percentage arithmetic at all:

- `portfolio_leaderboard_series` — one row per portfolio-day, already expressed as
  percent return from that portfolio's ranking anchor (`ROUND(((total_equity /
  NULLIF(anchor_equity, 0)) - 1) * 100, 4)`), joined to `portfolio_leaderboard` and
  filtered to `date >= anchor_date`.
- `spy_benchmark_series` — SPY, one row per session (last price of the day wins via
  `DISTINCT ON (date_trunc('day', fetched_at)::date)`), anchored at the earliest
  `anchor_date` the board used, so the benchmark starts on the same session as every
  portfolio.

Both are `security_invoker = true` and `GRANT SELECT` to `service_role` only, with
`REVOKE ALL` from `anon` and `authenticated`. The loader reads them directly; the
former `rebaseToAnchor` helper and the raw `portfolio_performance` / `price_history`
reads are gone.

The chart draws a numbered endpoint next to each line and a numbered legend, so a
series can be identified without relying on colour alone (WCAG 1.4.1).

## Freshness

The view is a plain view over `portfolio_performance`, which the engine writes
once per trading day. Nothing is cached in the web layer, so a page render always
reflects the last persisted snapshot; new portfolios enter the board as soon as
they have five daily observations with net movement.

## Pitfalls

- **New objects need a replica restart, not just a NOTIFY.** `docker/archive/nginx.secondary.conf`
  proxies `GET`/`HEAD` to the MiniPC replica's PostgREST, so anonymous page reads
  resolve there. DDL replicates, but `NOTIFY pgrst, 'reload schema'` cannot run on a
  standby (`cannot execute NOTIFY during recovery`) and does not propagate — the
  replica keeps answering `PGRST205` for the new object while the primary answers
  `200`. Restart it (`docker restart market-bench-archive-postgrest-replica`) and
  probe it directly: `curl -H "apikey: $KEY" 'http://localhost:3001/<view>?select=*&limit=1'`
  from the MiniPC. Probing only the public hostname proves nothing: it can be served
  by the primary, which is how a missing replica view reached production once.
- `CREATE OR REPLACE VIEW` cannot change column order or types; add a new column
  at the end or drop and recreate (this migration drops first).
- `PERCENTILE_CONT` is an ordered-set aggregate and cannot be used as a window
  function (`OVER is not supported`); compute the median in a scalar subquery.
- A failure here is not an empty board: the loader throws on the ranked or series
  read (the route logs it and marks the payload `degraded`, so the page says
  "unavailable" rather than "fills after the next close"), returns `spy: []` plus
  `spyUnavailable: true` when only the benchmark fails, and `trackedCount: null`
  when only the count fails. supabase-js resolves `{ data, error }` and never
  throws, so every read must check `.error` explicitly.

## Related

- [[entities/web-app]] — the homepage hero, chart, and leaderboard block
- [[entities/database]] — `portfolio_performance` and `portfolios` base tables
- [[concepts/zero-frontend-compute]] — ranking and rebasing stay in SQL / the loader
- [[concepts/deploy-skew-payload-tolerance]] — the nested-series normalization guard
- [[concepts/rendering-strategies]] — server-rendered SVG with no client chart library
