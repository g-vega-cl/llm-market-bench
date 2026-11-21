---
tags: [web, recipes, public-desk, api, analytics]
category: concept
---

# Recipe Public Stats & Desk

`fetchPublicDesk` used to assemble the public recipe desk payload for the homepage. That surface — and the module that served it — was deleted with the homepage in `684d1b5e`; the materialised tables (`recipe_public_stats`, `recipe_desk_summary`, `recipe_desk_feed`) are still rebuilt every runner cycle and are the only place the numbers exist, so any future public board reads them rather than the execution queue.

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

`RecipeDeskHomePage` used to render three regions — a hero proof card, a `TopPortfolios` leaderboard lane, and a live-bots tape. **All three were deleted with the homepage in `684d1b5e`.** The payload contract they consumed is still the right shape for any replacement surface: a spotlight with its compiled blocks, leaderboard rows with `medianReturnPct` / `worst` / `spy` / `trackedCount` / `windowDays` / `degraded`, and one tape row per bot carrying its return, `vs SPY`, open positions and resolved model.

## Pagination Discipline

The public-stats reads follow the same pagination discipline as the runner's enqueue path, because a PostgREST row cap silently truncates results rather than erroring:

- `_fetch_last_results(sb, recipe_ids)` pages `completed` `live_turn` rows in 500-row windows (up to 10 pages), stopping early once every requested recipe has a result or a short page arrives. A mid-page read error logs and returns whatever it has, so a partial board still refreshes.
- `_count_runs_today(sb, recipe_ids)` pages `completed` `live_turn` rows since midnight UTC in 1,000-row windows until a short page, so `runs_today` on the desk cannot quietly cap at 2,000.

## Analytics

The activation funnel's client-side terminus is the `run_queued` event, added to `AnalyticsEvent` in `apps/web/src/lib/analytics.ts` and fired from `RecipeStudioPage` immediately after a backtest job is enqueued (`track(posthog, 'run_queued', { recipeId, jobId })`). The runner settles the job server-side, where no PostHog client exists.

## Tests

That test was deleted with the module in `684d1b5e`. Its contract is worth restoring alongside any replacement surface: the owner's sentence beside each card, the newest bot spotlighted with its compiled blocks, unknown block types humanised, a failed prompt read surviving without losing cards, and zero reads of the execution queue.

## Related

- [[entities/web-app]] — dashboard hosting the desk
- [[entities/recipe-studio]] — recipe builder that writes descriptions and enqueues runs
- [[concepts/zero-frontend-compute]] — materialised rows only in the request path
- [[concepts/recipe-public-stats]] — public stats surface
