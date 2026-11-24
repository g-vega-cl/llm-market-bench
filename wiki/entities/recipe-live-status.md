---
tags: [recipes, push-v2, live, status, paper-portfolio, timezone, turbo, benchmark]
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
- **Portfolio Equity & Benchmark** — `LiveEquityBenchmarkSection` renders the recipe's `paper_equity_curve` through the shared [[entities/performance-chart]] `PerformanceChart`, with a `BenchmarkSelector` in the section header. See below.
- **Live Run Traces** — `RunSelectorBar` of the last 10 persisted `live_turn` jobs, each rendering stage prompt, per-round reasoning, tool calls & results, and full output through `TraceInspectorBlock`. Each stage header uses the fixed `LLM Call` label (no per-stage title). There is no inline `Latest Turn` option — the studio no longer runs live turns inline, so only persisted daemon runs appear here.
- **Turbo errors** — a failed activation renders an in-flow `role="alert"` danger trough above the portfolio block; the page never uses a modal or a floating tooltip.
- **Empty / Error State** — if the recipe has no live runs yet, the page renders a quiet trough ("No live runs yet. The first scheduled run will execute at the next 30-minute market-hours ET slot (09:30–16:00 ET)."). If the loader fails soft, the page renders the portfolio-less fallback without crashing.

## Portfolio Equity & Benchmark Section

`LiveEquityBenchmarkSection` (inside `RecipeLivePage.tsx`) turns the recipe's persisted equity checkpoints into a benchmarked performance chart. It renders only when the page has a portfolio (`hasPortfolio`).

- **Snapshot conversion** — `toLiveEquitySnapshots(equityCurve)` (`apps/web/src/features/recipes/utils/live-studio-helpers.ts`) maps `{ time, equity }` checkpoints into `{ date, total_equity }` snapshots, dropping any point whose timestamp cannot be normalized or whose equity is not finite, and sorting the survivors chronologically.
- **Timestamp normalization** — `normalizeEquityTimestamp(rawTime)` accepts the engine's Eastern-time checkpoint format (`2026-11-14 09:30 ET`, seconds optional) and rewrites it into a `Date.parse()`-safe ISO string with the correct DST offset, resolved by probing `America/New_York` with `Intl.DateTimeFormat(..., { timeZoneName: 'shortOffset' })` (so EST yields `-05:00` and EDT yields `-04:00`). An already-ISO timestamp passes through unchanged; anything unparseable returns `null`.
- **Benchmark window** — the section derives `rawStartDate` / `rawEndDate` from the first and last snapshot's `YYYY-MM-DD` prefix and only enables the benchmark when `hasMultiDayHistory` (start ≠ end). It calls `usePortfolioBenchmark` with `initialBenchmark: 'SPY'`, so the chart opens on the S&P 500 comparison; the `BenchmarkSelector` lets the viewer switch to another benchmark or to `None` (which renders the plain `Equity Curve`).
- **Day-1 notice** — a single-day curve renders the chart without a benchmark and an in-flow note: *"Benchmark comparison begins on Day 2 once 2+ trading days of history are recorded."* No benchmark fetch is issued in that case.
- **Empty state** — a recipe with no checkpoints renders an outlined card: *"No equity history available yet. Equity checkpoints are recorded after each live turn."*
- **Injection seam** — `RecipeLivePage` accepts an optional `benchmarkFetchFn` prop (defaulting to `getBenchmarkHistoryFn` from `apps/web/src/features/portfolios/api/benchmark-server-fn.ts`), so tests can supply a hermetic fetcher without touching the network.

## `liveMeta` Payload

`fetchLivePortfolioAndRuns` selects `id, user_id, name, is_live, turbo_expires_at, is_public, is_template, paper_cash, paper_positions, paper_trades, paper_equity_curve` and returns an additional `liveMeta` block:

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

The returned `portfolio` snapshot (`LivePortfolioSnapshot` in `apps/web/src/features/recipes/types.ts`) carries `cash`, `total_equity`, `open_positions`, `trades`, and an optional `equity_curve: { time: string; equity: number }[]` — the raw `paper_equity_curve` array (or `[]` when the column is null), which the equity section converts for the chart. `buildInlinePortfolio` in `live-studio-helpers.ts` populates the same field from an inline live run so the studio's inline snapshot and the live page agree.

## Turbo Activation

The page holds `turboExpiresAt`, `turboUsedToday`, `isActivatingTurbo`, `turboError`, and a `now` clock refreshed every 15 seconds. `handleActivateTurbo` calls `activateRecipeTurboFn({ data: { recipeId } })`, stores the returned `turboExpiresAt`, sets `turboUsedToday`, and surfaces any error through the alert trough. The `TurboButton` renders the 5-minute countdown while the window is live, `Turbo Used Today` once the daily allowance is spent, and a disabled `Turbo (Market Closed)` outside Mon–Fri `09:30–15:55 ET`. See [[concepts/recipe-turbo-mode]].

## Eastern-Time Formatting (`America/New_York`)

Every timestamp on the page is rendered in Eastern time through `formatEasternDateTime` (`~/utils/date`), never as a raw UTC slice:

- **Run selector labels** — each `RunSelectorBar` button is labeled `formatEasternDateTime(run.created_at)` (e.g. `Apr 6 • 5:32 AM ET`). When `created_at` is missing or formats to `Unknown`, the label falls back to the first 8 characters of the run id so the button is never blank.
- **Active-run slot badge** — the badge shows `activeRun.slot_label` when the run recorded one, otherwise `formatEasternDateTime(activeRun.as_of_utc)` instead of the previous truncated UTC ISO string.

Both DST halves must be correct, so the conversion is driven by `Intl.DateTimeFormat` with `timeZone: 'America/New_York'` rather than a fixed UTC offset. The same rule governs `normalizeEquityTimestamp`, which resolves the checkpoint offset per-date rather than assuming `-05:00`.

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

## Tests

- `apps/web/src/features/recipes/pages/RecipeLivePage.test.tsx` — Turbo activation states and market-hours gating, plus the equity section: the empty-history message, the default SPY comparison with a `+3.00% outperformance` readout, switching to QQQ and back to `None` (plain `Equity Curve`), and the single-day curve rendering the Day-1 notice with zero benchmark fetches. The suite wraps the page in a `QueryClientProvider` because the benchmark hook is a TanStack Query consumer.
- `apps/web/src/features/recipes/utils/live-studio-helpers.test.ts` — `normalizeEquityTimestamp` for EST (`-05:00`), EDT (`-04:00`), pass-through ISO, and unparseable input; `toLiveEquitySnapshots` dropping invalid points and sorting chronologically; `buildInlinePortfolio` emitting `equity_curve: []` when the run carries none.
- `apps/web/src/features/recipes/api/recipes-studio-api.test.ts` — `fetchLivePortfolioAndRuns` surfaces the persisted `paper_equity_curve` as `portfolio.equity_curve`.

## Related

- [[entities/recipe-studio]] — studio architecture, draft/save state machine, `BacktestError`, `StudioAlertSlot`, live switch confirmation
- [[entities/performance-chart]] — the shared chart and `usePortfolioBenchmark` hook the equity section renders
- [[concepts/recipe-turbo-mode]] — the 5-minute Turbo window, its RPC, and its market-hours helpers
- [[entities/secondary-minipc-edge]] — hosts the `recipe-worker` daemon that drains the `live_turn` lane with bounded concurrency
