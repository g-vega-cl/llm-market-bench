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
| `anchor_equity` | equity at the window open (last snapshot before it, else the first in-window one) |
| `last_equity` | last observed equity |
| `return_pct` | `(last_equity / anchor_equity - 1) * 100`, rounded to 4dp |
| `rank` | `RANK()` over `return_pct` descending, `portfolio_id` breaking ties |
| `window_days` | the trailing window, 30 |
| `median_return_pct` | median `return_pct` of the same population |

## Filters

- `observations >= 5` — a two-snapshot portfolio cannot win on noise.
- `owner_id <> 'test_model'` — the fixture portfolio is not a contestant.
- `last_equity <> anchor_equity` — a flat 10,000 account is excluded so a
  portfolio that never traded cannot rank above a real loser.

## Anchor, not first observation

Ranking and chart share one anchor: the last equity at or before the window
open, falling back to the first in-window snapshot for a portfolio younger than
30 days. Rebasing each series on its own first point hands a late starter a free
0% head start and makes two portfolios' returns incomparable.

## Access

`GRANT SELECT` to `service_role` only, and the view is `security_invoker = true`,
so base-table RLS stays in force if the read role ever stops bypassing it. The web
server fn reads the top five rows, then issues one `IN` query against
`portfolio_performance` for their series and rebases each on `anchor_equity` in
`apps/web/src/features/home/api/portfolio-leaderboard.ts`. Keeping the grant off
`anon` means the numbers cannot be read straight from the public PostgREST
surface; the page still shows them.

## Freshness

The view is a plain view over `portfolio_performance`, which the engine writes
once per trading day. Nothing is cached in the web layer, so a page render always
reflects the last persisted snapshot; new portfolios enter the board as soon as
they have five daily observations with net movement.

## Pitfalls

- DDL replicates to the MiniPC edge, but `NOTIFY pgrst, 'reload schema'` cannot be
  executed on a standby (`cannot execute NOTIFY during recovery`) and does not
  propagate. Issue it on the primary; the public edge (`benchify-archive-db.clvg.uk`)
  is served by the primary's PostgREST.
- `CREATE OR REPLACE VIEW` cannot change column order or types; add a new column
  at the end or drop and recreate (this migration drops first).
- `PERCENTILE_CONT` is an ordered-set aggregate and cannot be used as a window
  function (`OVER is not supported`); compute the median in a scalar subquery.
- A failure here is not an empty board: the loader logs it and marks the payload
  `degraded`, so the page says "unavailable" rather than "fills after the next close".
