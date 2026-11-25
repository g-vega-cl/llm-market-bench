---
tags: [recipes, push-v2, live, status, paper-portfolio, timezone, turbo, public-read]
category: entity
---

# Recipe Live Status Page (`/recipes/live/$recipeId`)

The dedicated live-status page for a Push v2 strategy. It is now a **public-capable root route** (moved out of `/_authed`) that shares the `BotStageHeader` living-scene hero with the Bot Overview and Blueprint pages, so a visitor can inspect a public/template bot's live runs while owner-only controls stay gated. The studio (`/recipes`) remains a pure editor; the live page focuses on run traces and the paper ledger without background polling or SSE.

## Route

- **Files**: `apps/web/src/routes/recipes/live/$recipeId/route.tsx` (Outlet layout), `index.tsx` (the hub, path `/recipes/live/$recipeId/`), and `runs.tsx` (the detail page, `/recipes/live/$recipeId/runs`). Previously a single root-level file at `apps/web/src/routes/recipes/live/$recipeId.tsx`.
- **Hub vs detail**: the hub renders the shared card plus `BotSummaryStrip` (Total Equity, Cash, Open Positions, Latest Run) and a single `Run traces, portfolio & closed trades →` link; `runs` renders the same card-less chrome through `BotSceneShell` and holds the traces, portfolio and closed trades. Both use the same `fetchLivePortfolioAndRunsFn` fetch, so a navigation costs one load, not two.
- **Loader**: calls `fetchLivePortfolioAndRunsFn({ data: { recipeId } })`, failing soft to `null`. It resolves `initialAtmosphere` server-side via `resolveAtmospherePhase(new Date(), 'market-et')` (zero-flash hydration), and — only when the caller is the signed-in owner — fetches `fetchRecipeQuotaStatusFn()` and `fetchUserRecipesFn()` in parallel.
- **Access**: a non-owner may read a recipe that is `is_public` or `is_template`; the owner's `user_id` is never leaked to a non-owner. A private recipe, or a missing row, resolves to `null` and renders an `ErrorCard` with a back-to-My-Bots link. Owner actions (Backtest, live toggle, Turbo) are gated on `liveMeta.isOwner`.

## Shared header (`BotStageHeader` + `BotStageSubNav`)

`apps/web/src/features/recipes/components/BotStageHeader.tsx` replaces the former `LiveStatusHeader`. It renders a `SceneStage` (`variant="hero"`, `backdropMode="page"`, `motionRole="reactive"`, `scrim="panel"`) over `CedarRidgeBackdrop` with `SceneHudControls` — the ridge world is a fixed full-viewport layer behind the page so the run traces begin directly under the card, and `fauna="standby"` freezes the patrol and dims the beacons when the bot is not live. It contains:

- a `← My Bots` link and the live-state badge — `Live: PAUSED` (neutral), `Turbo: <N>m left (5m)` (solid accent, `suppressHydrationWarning`), or `Live: ON (30m)` (solid success);
- the recipe name/description, a `Live: 30m • Backtest: <cadence> • 1 LLM call` line, and a `Next run:` label (`Paused`, `within 5m (Turbo)`, or `getNextLiveSlotLabel(now)`);
- owner action buttons — Backtest (`resolveBacktestButtonLabel`), the live toggle (`Enabling Live...` / `Pausing Live...` in-flight labels), and `TurboButton` (only on the live tab while live);
- `LiveSwitchConfirmation` (the 3-live-cap switch), `StudioAlertSlot`, and fork/extra-error alerts;
- `BotStageSubNav` (`BotStageSubNav.tsx`) — `Overview` / `Live Runs` / `Blueprint` links (`aria-current="page"` on the active tab; Blueprint only for owners).

All owner actions route through `useBotHeaderActions` (`apps/web/src/features/recipes/utils/use-bot-header-actions.ts`), which wraps `useLiveScheduleControl` and the backtest/fork/pledge server functions.

## Page content

The hub itself carries no panels — `BotSummaryStrip` shows Total Equity, Cash, Open Positions and the Latest Run stamp with its signal count, and one link opens the detail page. Everything below lives on `/recipes/live/$recipeId/runs`:

- **Live Run Traces** (`LiveRunTracesSection`) — a Card describing the 30m/5m cadence, a run-stamp badge (Eastern `as_of_utc`, falling back to `created_at`) plus signal count, `RunPaginator` one-at-a-time paging (`← Older · N of M · Newer →`, boundary buttons inert via `aria-disabled` but focusable), and one recessed `.voxel-trough` per stage rendered through `TraceInspectorBlock` under a fixed `LLM Call` label. A queued/failed run with no `result_json` renders `no trace output yet (status: …)` plus its `error_message`.
- **Live Paper Portfolio + Closed Trades** — when a portfolio snapshot exists, a Card renders `RecipePortfolioBlock` (`embedded`, so no duplicate metric tiles) titled `Live Paper Portfolio`, followed by `ClosedTradesSection` titled `All Closed Live Trades` (in-flow `.voxel-trough` catalyst/confidence inspection, zero floating tooltips).

The former `LiveStatusHeader` and `LiveEquityBenchmarkSection` are gone from this page — the equity curve and benchmark comparison now live on the Bot Overview page (`/recipes/$recipeId`, see [[entities/recipe-studio]]).

## `liveMeta` payload

`fetchLivePortfolioAndRuns` returns a `liveMeta` block (`LiveStatusMeta` in `apps/web/src/features/recipes/types.ts`) extended for the shared header:

```ts
interface LiveStatusMeta {
    recipeName: string;
    description?: string;
    cadence?: RecipeCadence;
    isLive: boolean;
    isOwner: boolean;
    isPublic?: boolean;
    isTemplate?: boolean;
    turboExpiresAt: string | null;
    turboUsedToday: boolean;
}
```

`turboUsedToday` is resolved for the owner only (`readTurboUsedToday` reads `recipe_user_quotas.last_turbo_et_date` and compares against `getEtDateString(new Date())`); non-owners always receive `false` and never see the Turbo control.

## Public read & bounded caching (`fetchLivePortfolioAndRuns`)

`fetchLivePortfolioAndRuns(recipeId, userId: string | null)` accepts a nullable user. Non-owner reads of public/template recipes are served from a bounded 30-second in-memory cache (`publicLiveCache`, max 50 entries, oldest-evicted) so a public bot's live page survives repeated anonymous navigation without re-querying; the cache is dropped by `invalidatePublicRecipeCache(recipeId)` on every save, archive, live toggle, live switch, and Turbo activation (see [[concepts/atomic-live-schedule-switch]]). Owner reads are never cached.

## Turbo activation

The page holds `turboExpiresAt`, `turboUsedToday`, `isActivatingTurbo`, `turboError`. `handleActivateTurbo` calls `activateRecipeTurboFn({ data: { recipeId } })`, stores the returned `turboExpiresAt`, sets `turboUsedToday`, and surfaces errors through the header's alert slot. `TurboButton` renders the 5-minute countdown, `Turbo Used Today`, or a disabled `Turbo (Market Closed)` outside Mon–Fri `09:30–15:55 ET`. See [[concepts/recipe-turbo-mode]].

## Eastern-Time Formatting (`America/New_York`)

Every timestamp renders in Eastern time. `runStampLabel(job, run)` formats `run.as_of_utc ?? job.created_at` through `formatEasternDateTime`, falling back to the job id prefix; the daemon's raw `slot_label` never reaches the DOM. Both DST halves are correct because the conversion uses `Intl.DateTimeFormat` with `timeZone: 'America/New_York'`.

## Next-Run Label & Market Hours

`getNextLiveSlotLabel(now)`, `formatTurboRemainingLabel`, and `LIVE_CADENCE_LABEL` live in `apps/web/src/features/recipes/utils/market-hours.ts` and derive the next 30-minute ET slot (`<HH:MM> ET today`, `09:30 ET tomorrow`, `09:30 ET Monday`, or `09:30 ET next trading day`), honoring weekends and the US holiday set (including Good Friday).

## Why a separate page

- **Studio separation of concerns**: `/recipes` is configuration; live monitoring is observational.
- **No polling**: the daemon executes on the 30-minute market-hours ET cadence (and 5-minute Turbo when boosted); the page refreshes by navigation/reload.
- **Public read, owner write**: anyone can view a shared bot's live runs; only the owner sees Backtest / live / Turbo / Blueprint.
- **Max 3 live recipes**: enabling live while three are already live surfaces `LiveSwitchConfirmation` in the header; the switch pauses the old recipe (clearing its Turbo window) then enables the new one. See [[concepts/atomic-live-schedule-switch]].

## Tests

- `apps/web/src/features/recipes/pages/RecipeLivePage.test.tsx` — empty state inside the `SceneStage` header, live paper portfolio + `All Closed Live Trades` + trace paging (`RunPaginator`, `LLM Call`, `no trace output yet`), the `Overview` / `Live Runs` / `Blueprint` sub-nav links, Turbo activation and market-closed gating.

## Related

- [[entities/recipe-studio]] — studio, Bot Overview, and `/build` workspace
- [[entities/performance-chart]] — the chart now rendered on the Bot Overview page
- [[concepts/recipe-turbo-mode]] — the Turbo window and its RPC
- [[concepts/atomic-live-schedule-switch]] — the live switch and cache invalidation
- [[entities/secondary-minipc-edge]] — hosts the `recipe-worker` daemon
