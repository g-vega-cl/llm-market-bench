---
tags: [web, recipes, public-desk, api, analytics]
category: concept
---

# Recipe Public Stats & Desk

`fetchPublicDesk` (`apps/web/src/features/recipes/api/public-board-api.ts`) assembles the public recipe desk payload served to the homepage. It reads only materialised rows — never the execution queue — so the request path performs zero compute.

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

`RecipeDeskHomePage` renders three regions:

1. **Hero proof** — `BuildProof` receives the spotlight and the fork handler, replacing the old equity-chart hero.
2. **Leaderboard** — `TopPortfolios` receives `rows`, `medianReturnPct`, `worst`, `spy`, `trackedCount`, `windowDays`, and `degraded` (see [[concepts/portfolio-leaderboard-view]]).
3. **Live bots tape** — `BotRow` renders one `<li>` per bot: LIVE badge, name, the owner's description (or the last action), return, `vs SPY`, open-position count, the model label, and a Fork button.

## Analytics

The activation funnel's client-side terminus is the `run_queued` event, added to `AnalyticsEvent` in `apps/web/src/lib/analytics.ts` and fired from `RecipeStudioPage` immediately after a backtest job is enqueued (`track(posthog, 'run_queued', { recipeId, jobId })`). The runner settles the job server-side, where no PostHog client exists.

## Tests

`public-board-api.test.ts` pins: the owner's sentence carried beside each card, the newest bot with a prompt spotlighted with its compiled blocks, unknown block types humanised, a failed prompt read surviving without losing cards, and zero reads of the execution queue.

## Related

- [[entities/web-app]] — dashboard hosting the desk
- [[entities/recipe-studio]] — recipe builder that writes descriptions and enqueues runs
- [[concepts/portfolio-leaderboard-view]] — leaderboard lanes rendered beside the desk
- [[concepts/zero-frontend-compute]] — materialised rows only in the request path
- [[concepts/recipe-public-stats]] — public stats surface
