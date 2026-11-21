---
tags: [web, recipes, public-desk, api, analytics]
category: concept
---

# Recipe Public Stats & Desk

`fetchPublicDesk` (`apps/web/src/features/recipes/api/public-board-api.ts`) assembles the public recipe desk payload. It reads only materialised rows — never the execution queue — so the request path performs zero compute.

## PublicDesk Contract

```ts
interface PublicDesk {
    cards: PublicBoardCard[];
    feed: PublicDeskFeedItem[];
    liveCount: number;
    beatSpyCount: number;
    medianReturnPct: number | null;
    spotlight: PublicSpotlight | null;
}
```

`PublicBoardCard` carries `recipeId`, `name`, `description` (the owner's sentence, or `null`), `returnPct`, `spyReturnPct`, `tradeCount`, `lastAction`, `runsToday`, `openPositions`, and `resolvedModel`.

`PublicSpotlight` carries `recipeId`, `name`, `prompt`, `blocks: string[]`, `returnPct`, and `spyReturnPct`.

`PublicDeskFeedItem` carries `recipeId`, `name`, `action`, and `ticker`.

## Sources

- `recipe_desk_stats` (materialised) — cards and summary counts (`live_count`, `beat_spy_count`, `median_return_pct`)
- `recipe_desk_feed` — the recent-fills feed
- `strategy_recipes` — `id, description, graph_json, updated_at` for the card ids only

The `strategy_recipes` read is best-effort: a failed read degrades to no excerpt and never costs the desk its cards.

## blockLabels

`blockLabels(graph)` walks `graph_json.stages[].blocks[]`, collects distinct block types in graph order, caps at five, and humanises them through `BLOCK_LABELS` (`memories` → `Memories`, `news` → `News`, `output_format` → `Output`, `prompt` → `Prompt`, `technicals` → `Technicals`). Unknown types fall back to `type.replace(/_/g, ' ')` rather than being dropped or shown raw.

## Spotlight

The spotlight is the most recently active card that has a written description: its `prompt` is that description and its `blocks` come from `blockLabels(graph_json)`. When no card has a description the spotlight is `null` — the proof shown above the fold must be real or absent.

## Desk Rendering

The desk is no longer the homepage. `/` is the [[entities/recipe-playground]] bot builder; the public board lives at `/live-desk` (`apps/web/src/routes/live-desk.tsx`), which loads through the same `getHomePayload()` server function and renders two regions:

1. **Every running bot** — a `BotRow` `<li>` per card: name, return, `vs SPY`, open-position count, and the last action (or `no fills yet`). The header line reads `{liveCount} live · {beatSpyCount} beating SPY · losers are published beside winners.`
2. **Agent portfolios, same window** — `TopPortfolios` receives `rows`, `medianReturnPct`, `worst`, `spy`, `trackedCount`, `windowDays`, and `degraded` (see [[concepts/portfolio-leaderboard-view]]).

The homepage keeps a compact `ProofStrip` instead: `pickProof(leaderboard)` publishes the top row and the board's own `worst` row side by side with the as-of date, plus a `Full desk →` link to `/live-desk`.

## Pagination Discipline

The public-stats reads follow the same pagination discipline as the runner's enqueue path, because a PostgREST row cap silently truncates results rather than erroring:

- `_fetch_last_results(sb, recipe_ids)` pages `completed` `live_turn` rows in 500-row windows (up to 10 pages), stopping early once every requested recipe has a result or a short page arrives. A mid-page read error logs and returns whatever it has, so a partial board still refreshes.
- `_count_runs_today(sb, recipe_ids)` pages `completed` `live_turn` rows since midnight UTC in 1,000-row windows until a short page, so `runs_today` on the desk cannot quietly cap at 2,000.

## Analytics

The activation funnel's client-side terminus is the `run_queued` event, added to `AnalyticsEvent` in `apps/web/src/lib/analytics.ts` and fired from `RecipeStudioPage` immediately after a backtest job is enqueued (`track(posthog, 'run_queued', { recipeId, jobId })`). The runner settles the job server-side, where no PostHog client exists. The playground adds its own funnel events (`playground_run`, `playground_run_blocked`, `playground_preset_applied`, `playground_describe_used`, `playground_describe_failed`, `describe_it_failed`).

## Tests

`public-board-api.test.ts` pins: the owner's sentence carried beside each card, the newest bot with a prompt spotlighted with its compiled blocks, unknown block types humanised, a failed prompt read surviving without losing cards, and zero reads of the execution queue.

## Related

- [[entities/web-app]] — dashboard hosting `/live-desk`
- [[entities/recipe-playground]] — the homepage builder that replaced the desk
- [[entities/recipe-studio]] — recipe builder that writes descriptions and enqueues runs
- [[concepts/portfolio-leaderboard-view]] — leaderboard lanes rendered beside the desk
- [[concepts/zero-frontend-compute]] — materialised rows only in the request path
- [[concepts/recipe-public-stats]] — public stats surface
