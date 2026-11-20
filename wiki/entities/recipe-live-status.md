---
tags: [recipes, push-v2, live, status, paper-portfolio, timezone, turbo]
category: entity
---

# Recipe Live Status Page (`/recipes/live/$recipeId`)

The dedicated live-status page for a Push v2 strategy. Previously live paper portfolio and run traces lived inline on the Studio (`/recipes`), which conflated configuration with live-run monitoring and forced the studio to poll for updates. The live view now has its own route, server-rendered through `RecipeLivePage`, so the studio stays a pure editor and the live page can focus on portfolio and run history without background polling or SSE.

## Route

- **File**: `apps/web/src/routes/_authed/recipes/live/$recipeId.tsx`
- **Loader**: `useLoaderData` seeds `RecipeLivePage` via `fetchLivePortfolioAndRunsFn({ data: { recipeId } })`. The call fails soft to `null`, so a missing or stale recipe never breaks the page.
- **Auth**: guarded like all `/_authed` routes; the loader redirects to login when the user is not signed in.

## Entry Points

The live status page is reachable from three places in the studio:

- **`StudioActionBar`** — when the open recipe is currently scheduled live (`isCurrentlyScheduledLive`), a `Live Status →` link and `TurboButton` (`⚡ Turbo (5m x 1h)`) are rendered next to the `Live: ON (30m)` toggle, pointed at `/recipes/live/$recipeId` with the open recipe's id via `liveRecipeId` (passed by `RecipeStudioPage` as `strategy.id` while live).
- **`SavedRecipesStrip` (My Strategies)** — every strategy chip whose `RecipeSummaryItem.is_live` is true also renders a badge and a `Live Status →` link to its own live page. The badge reads `TURBO 5m` (accent) while `isTurboActive(item.turbo_expires_at)` is true and `LIVE 30m` (success) otherwise.
- **`RecipeAlertsInbox`** — the recipe name on each alert card is a `Link` to `/recipes/live/$recipeId` when the alert carries a `recipe_id`; otherwise the name renders as plain text.

## Page Content

- **Header (`LiveStatusHeader`)** — a `← Back to Studio` link, the `Live Status` heading, the short recipe id, a live-state badge, a `Next run: <label>` string, and the `TurboButton` for the owner. The badge is `Live: PAUSED` (soft neutral) when `liveMeta.isLive` is false, `Turbo: <N>m left (5m)` (solid accent) while a Turbo window is active, and `Live: ON (30m)` (soft success) otherwise. The `Next run:` label reads `Paused`, `within 5m (Turbo)`, or the next 30-minute slot label. The `← Back to Studio` link carries `search={{ recipeId }}` so it returns to `/recipes?recipeId=<recipeId>` and reopens this strategy in the studio rather than landing on a fresh draft.
- **Live Paper Portfolio** — `RecipePortfolioBlock` fed by `paper_cash` / `paper_positions` / `paper_trades`, with every open position enriched by the latest mark price.
- **Live Run Traces** — `RunSelectorBar` of the last 10 persisted `live_turn` jobs, each rendering stage prompt, per-round reasoning, tool calls & results, and full output through `TraceInspectorBlock`. Each stage header uses the fixed `LLM Call` label (no per-stage title). There is no inline `Latest Turn` option — the studio no longer runs live turns inline, so only persisted daemon runs appear here.
- **Turbo errors** — a failed activation renders an in-flow `role="alert"` danger trough above the portfolio block; the page never uses a modal or a floating tooltip.
- **Empty / Error State** — if the recipe has no live runs yet, the page renders a quiet trough ("No live runs yet. The first scheduled run will execute at the next 30-minute market-hours ET slot (09:30–16:00 ET)."). If the loader fails soft, the page renders the portfolio-less fallback without crashing.

## `liveMeta` Payload

`fetchLivePortfolioAndRuns` selects `id, user_id, name, is_live, turbo_expires_at, is_public, is_template, paper_cash, paper_positions, paper_trades` and returns an additional `liveMeta` block:

```ts
interface LiveStatusMeta {
    recipeName: string;
    isLive: boolean;
    isOwner: boolean;
    turboExpiresAt: string | null;
    turboUsedToday: boolean;
}
```

`turboUsedToday` is resolved for the owner only, by reading `recipe_user_quotas.last_turbo_et_date` in parallel with the run query and comparing it against `getEtDateString(new Date())`. Non-owners always receive `turboUsedToday: false` and never see the Turbo control.

## Turbo Activation

The page holds `turboExpiresAt`, `turboUsedToday`, `isActivatingTurbo`, `turboError`, and a `now` clock refreshed every 15 seconds. `handleActivateTurbo` calls `activateRecipeTurboFn({ data: { recipeId } })`, stores the returned `turboExpiresAt`, sets `turboUsedToday`, and surfaces any error through the alert trough. The `TurboButton` renders the 5-minute countdown while the window is live, `Turbo Used Today` once the daily allowance is spent, and a disabled `Turbo (Market Closed)` outside Mon–Fri `09:30–15:55 ET`. See [[concepts/recipe-turbo-mode]].

## Eastern-Time Formatting (`America/New_York`)

Every timestamp on the page is rendered in Eastern time through `formatEasternDateTime` (`~/utils/date`), never as a raw UTC slice:

- **Run selector labels** — each `RunSelectorBar` button is labeled `formatEasternDateTime(run.created_at)` (e.g. `Apr 6 • 5:32 AM ET`). When `created_at` is missing or formats to `Unknown`, the label falls back to the first 8 characters of the run id so the button is never blank.
- **Active-run slot badge** — the badge shows `activeRun.slot_label` when the run recorded one, otherwise `formatEasternDateTime(activeRun.as_of_utc)` instead of the previous truncated UTC ISO string.

Both DST halves must be correct, so the conversion is driven by `Intl.DateTimeFormat` with `timeZone: 'America/New_York'` rather than a fixed UTC offset.

## Next-Run Label (`getNextLiveSlotLabel`) & Market Hours (`utils/market-hours.ts`)

`getNextLiveSlotLabel(now: Date)` lives in `apps/web/src/features/recipes/utils/market-hours.ts` and derives the next scheduled 30-minute slot (14 slots, `09:30` through `16:00 ET`) from the real ET wall clock, returning `<HH:MM> ET today`, `09:30 ET tomorrow`, `09:30 ET Monday`, or `09:30 ET next trading day`:

- It resolves the ET date, weekday, hour, and minute via `getEtClockParts` (`Intl.DateTimeFormat` with `timeZone: 'America/New_York'`).
- `Sat` / `Sun` → `09:30 ET Monday`.
- US holidays (`isKnownUsMarketHolidayEt`, which includes Good Friday) → `09:30 ET next trading day`.
- Otherwise the next slot is the first of the 14 half-hour slots strictly greater than the current ET minute-of-day.
- If no slot remains today, `Fri` → `09:30 ET Monday`; any other weekday → `09:30 ET tomorrow`.

`RecipeLivePage.test.tsx` and `market-hours.test.ts` pin this behavior with fake timers across boundaries: 15:50 EST Wednesday → `16:00 ET today`, 16:05 EST Wednesday → `09:30 ET tomorrow`, 12:00 EST Wednesday → `12:30 ET today`, 16:05 EST Friday → `09:30 ET Monday`, and Saturday → `09:30 ET Monday`.

## Why a Separate Page

- **Studio separation of concerns**: `/recipes` is the configuration surface (templates, blocks, tools, save, backtest enqueue, live toggle, Turbo boost). Live monitoring is observational and belongs elsewhere.
- **No polling**: the studio no longer polls for live turns. The daemon handles live execution on the 30-minute market-hours ET cadence (and 5-minute Turbo cadence when boosted), and the live page is refreshed by navigation or reload.
- **Max 3 live recipes**: enabling Scheduled Live while three recipes are already live fails with `Scheduled live limit reached (3/3)`. Enabling it while another recipe is live triggers `LiveSwitchConfirmation` (inline trough, not a modal) in the Studio; the switch disables the old recipe first (clearing its `turbo_expires_at`), then enables the new one, then navigates here.

## Related

- [[entities/recipe-studio]] — studio architecture, draft/save state machine, `BacktestError`, `StudioAlertSlot`, live switch confirmation
- [[concepts/recipe-turbo-mode]] — the 5-minute Turbo window, its RPC, and its market-hours helpers
- [[entities/secondary-minipc-edge]] — hosts the `recipe-worker` daemon that drains the `live_turn` lane with bounded concurrency
