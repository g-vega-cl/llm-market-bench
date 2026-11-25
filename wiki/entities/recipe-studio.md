---
tags: [recipes, push-v2, trading, backtest, news-corpus, voxel, studio]
category: entity
---

# Recipe Studio

The **Recipe Studio** is a multi-surface experience built around a shared living-scene header (`BotStageHeader`):

1. **`/build` — The Chat Builder** (primary entry point)
   - Steps 1–2 render on the design-system `SceneStage` (`variant="hero"`, `motionRole="reactive"`) over the canvas-free `CedarRidgeBackdrop` (six SVG/CSS planes, pointer-and-scroll drift, patrolling lantern-bot and fox) with `SceneHudControls`, inside a `.scene-scrim .voxel-card`
   - Action-first ordering (§4b): visitors immediately see the compact `STEP 1 · NOW` status strip and auto-expansible `<textarea>` + `Continue to Alignment →` CTA at the top, with one-tap starter chips (an intrinsic `repeat(auto-fit, minmax(min(100%, 7.5rem), 1fr))` grid) and `BuilderStepper` (`1. Describe` → `2. Align` → `3. Backtest & Go Live`) below
   - Compiles into a validated Push v2 recipe (one LLM call, point-in-time news, paper cash) with a real-phase `BuilderCompilePipeline`
   - Step 2 presents one round of 3–5 tailored multiple-choice alignment questions (`BuilderAlignmentCard`) before compiling the final bot
   - On success, shows a **Compiled Bot Workspace** summary `.voxel-card` inside `PageLayout` over `GlobalBackground`, with a single primary CTA: "▶ Backtest (Random 2W)" and a calm lower workspace switching between `Blocks & Tools` and `Prompt Preview`
   - **`/build` is always a fresh describe flow**: a `/build?recipeId=<id>` request now `beforeLoad`-redirects to `/recipes/$recipeId` (the Bot Overview). After saving an unsaved compiled bot, `CompiledBotWorkspace` navigates to `/recipes/$recipeId`.
   - Accessible from `/lab` directory and the homepage CTA

2. **`/recipes/$recipeId` — Bot Overview hub** (public-capable for `is_public`/`is_template` bots)
   - One card, one purpose: `BotStageHeader` (`SceneStage` + `CedarRidgeBackdrop` + the `Overview | Performance | Behaviour | Live Runs | Blueprint` chip row) plus `BotSummaryStrip` — Total Equity, Net Return, Win Rate, Open Positions — and a single `Performance, behaviors & positions →` link into the detail page. The hub renders **no panels**.
   - Loads via `fetchRecipeOverviewFn` (30s bounded public cache)
   - Non-owners receive a read-only view with a `Fork to My Bots` action; owner actions (Backtest, live toggle, Turbo, Blueprint) are gated on `isOwner`

2a. **`/recipes/$recipeId/performance` — Performance tab** (public-capable; same payload, its own loader): equity vs benchmark, open positions, closed trades.  
2b. **`/recipes/$recipeId/behavior` — Behaviour tab** (public-capable, same `fetchRecipeOverviewFn` loader): tool usage, action mix, ticker focus, exit reasons; renders an empty state before the first run.
   - Chrome is `BotSceneShell` (page-level Cedar Ridge world, `← <bot name>` back link, sub-nav in `currentMode="item"` so the active chip claims `aria-current="true"` rather than `page`), then the three Matcha & Voxel blocks that used to sit under the hub card:
     - **Performance & Equity** (`PerformanceOverviewBlock` + `PerformanceChart` + benchmark selector)
     - **Behaviors & Insights** (`BotBehaviorsBlock` powered by `recipe-insights.ts` over up to 50 slimmed live turns or latest backtest)
     - **Open Positions + Recent 5 Closed Trades** (`ClosedTradesSection` with in-flow trough inspection, trailing link to `/recipes/live/$recipeId/runs`) + **Recent Backtests & Strategy DNA** (`OverviewBottomSection`)
   - Because those panels own the Enable Live and Run Backtest buttons, the shell's `alerts` slot carries the hub card's feedback with them: `LiveSwitchConfirmation` at the 3-live cap, `StudioAlertSlot` quota/execution errors, and a `role="alert"` fork error. `WaitlistPledgeModal` mounts outside the shell.

3. **`/recipes/$recipeId/edit` — Blueprint Editor** (owner-only)
   - `RecipeEditPage` shares `BotStageHeader` (Blueprint tab active) and renders `RecipeNameField` + `CompiledBotBlueprintSection` (Blocks & Tools / Prompt Preview)
   - Stays a single page on purpose: its below-card content is the editor (`StageBuilder` with `onStageChange`), not a data dump, so a hub/detail split would add a click before every edit
   - Reached only by the owner; a non-owner renders an `ErrorCard`

4. **`/recipes/live/$recipeId` — Live Runs hub** (public-capable for `is_public`/`is_template` bots)
   - `BotStageHeader` (`TurboButton` for owners) plus `BotSummaryStrip` — Total Equity, Cash, Open Positions, Latest Run (stamp + signal count) — and one `Run traces, portfolio & closed trades →` link into the detail page
   - Moved from `/_authed/recipes/live/$recipeId` to root-level `/recipes/live/$recipeId`; non-owners may read public/template recipes

4a. **`/recipes/live/$recipeId/runs` — Live Runs tab** (public-capable; same payload, its own loader); the Live hub at `/recipes/live/$recipeId` now redirects here
   - Chrome is `BotSceneShell` (`parent="live"`, back link to the Live hub, `sectionTitle="Run traces & portfolio"` for the `sr-only` `<h1>`, sub-nav in `currentMode="item"`), then paginated `Live Run Traces` (`RunPaginator` + `TraceInspectorBlock`), embedded `Live Paper Portfolio`, and `All Closed Live Trades`
   - This is where the ~4,000 px of run output belongs: it was the bulk of the old Live page and made that page serve two purposes at once

5. **`/recipes` — My Bots Dashboard** (signed-in users only)
   - Lists the user's saved strategies with minimal per-bot cards
   - Primary CTA: "+ Build New Bot" → `/build`
   - Each bot links to `/recipes/$recipeId` (Bot Overview), `/recipes/$recipeId/edit` (Blueprint Editor), and `/recipes/live/$recipeId/runs` (Live Runs & Traces)
   - Live schedule toggles, Turbo boost, backtest history, and alerts inbox
   - Anonymous visitors see the **Recipe Gallery** (read-only template catalogue with a single "Start Building Your Bot →" CTA to `/build`)

## Architecture

### 1. Storage & Corpus (unchanged)
- `public.recipe_news_corpus`: Point-in-time news articles with `search_tsv` and GIN indexes
- `public.strategy_recipes`: Push v2 strategy configurations (`graph_json` with `version: "2.0-push"`, single `stages` item), cadence (default `3h`), `turbo_expires_at`, concurrency limits, isolated paper ledgers
- `public.recipe_intraday_bars`: Cached intraday bars for backtesting and live snapshots
- `public.recipe_execution_queue`: Priority queue with counted dual-lane dequeue (`pop_next_recipe_job`), 3 concurrent backtests, 1 open live turn per recipe
- `public.recipe_user_quotas`: Per-user quotas (2 backtests/day, 3 live bots, 1 Turbo/day via `activate_recipe_turbo`)
- `public.recipe_alerts_inbox`, `public.recipe_waitlist_pledges`, `public.recipe_showcase`
- `public.recipe_public_stats` / `public.recipe_desk_summary` / `public.recipe_desk_feed`: Runner-materialised board
- `public.recipe_builder_usage` + `consume_builder_compile`: Atomic 25 compiles/day metering
- `public.recipe_ops_events`: Scheduler telemetry

### 2. Engine Processing (`apps/engine/recipes/`) — unchanged core
- `push_schema.py`: Pydantic models for Push v2 (`PushStrategy`, `StrategyStage`, blocks). Exactly one stage enforced.
- `push_hydrator.py`: Point-in-time filtering and stage prompt hydration. Renders `prompt` blocks first, data blocks in the middle, and `output_format` blocks last.
- `portfolio_engine.py`: Shared Long-Only simulator (`PortfolioState`, `apply_portfolio_step`), whole-share sizing, Alpaca mirror
- `intraday_bars.py`: 3x/day ET slot expansion for backtests, live slot capture
- `pit_tools.py`: Strict point-in-time tool dispatcher for backtests
- `llm_caller.py`: Extracted LLM failover caller (`auto-go` → free proxy, no Strata contention)
- `push_runner.py` & `backtest_accounting.py`: Single-call live execution and 10-day backtests
- `worker.py`: `async_process_next_recipe_job` with optimistic CAS persistence
- `runner.py`: MiniPC dual-lane daemon (30m live slots + 5m Turbo + 5s queue poll)
- `public_stats.py`: Rebuilds materialised board tables after each lane drain
- `news_corpus.py`: Live news sync from market wires + newsletter snapshots

### 3. Presentation — Shared Header & Surfaces

#### Shared `BotStageHeader` + `BotStageSubNav`
`apps/web/src/features/recipes/components/BotStageHeader.tsx` is the single living-scene header shared by the Overview hub. Every other tab renders `BotSceneShell` instead: the card, its actions and Turbo are the Overview's own, and the chip row is the navigation to the rest. It renders a `SceneStage` (`variant="hero"`, `backdropMode="page"`, `motionRole="reactive"`, `scrim="panel"`) over `CedarRidgeBackdrop` with `SceneHudControls`: the world is a fixed full-viewport layer behind the page, the stage is content-height (card + its controls row, no band), and each page's `PageLayout` carries `relative z-10` so the tab panel starts 24 px under the card. It contains:
- a `← My Bots` link and the live-state badge — `Live: PAUSED` (neutral), `Turbo: <N>m left (5m)` (solid accent, `suppressHydrationWarning`), or `Live: ON (30m)` (solid success);
- the recipe name/description, a `Live: 30m • Backtest: <cadence> • 1 LLM call` line, and a `Next run:` label (`Paused`, `within 5m (Turbo)`, or `getNextLiveSlotLabel(now)`);
- owner action buttons — Backtest (`resolveBacktestButtonLabel`), the live toggle (`Enabling Live...` / `Pausing Live...` in-flight labels), and `TurboButton` (only on the live tab while live);
- `LiveSwitchConfirmation` (the 3-live-cap switch), `StudioAlertSlot`, and fork/extra-error alerts;
- `BotStageSubNav` (`BotStageSubNav.tsx`) — `Overview` / `Live Runs` / `Blueprint` links (Blueprint only for owners). The active chip's announcement is driven by `currentMode: 'page' | 'item' | 'none'` (which replaced the `markCurrent` boolean): `page` on the hub, where the chip's href is the current URL, emits `aria-current="page"`; `item` on a detail tab emits `aria-current="true"`, because the chip styles as the current section but links to the hub; `none` leaves it unmarked.

All owner actions route through `useBotHeaderActions` (`apps/web/src/features/recipes/utils/use-bot-header-actions.ts`), which wraps `useLiveScheduleControl` and the backtest/fork/pledge server functions.

#### `BotSceneShell` — detail-tab chrome
`apps/web/src/features/recipes/components/BotSceneShell.tsx` is the chrome for every non-Overview bot tab (Performance, Behaviour, Live Runs). It mounts the same page-level `SceneStage` + `CedarRidgeBackdrop` + `SceneHudControls` world as the hub, then a header row and the panel:
- a required `sectionTitle` becomes the page's own `<h1 className="sr-only">{recipeName} — {sectionTitle}</h1>`, so a detail tab has a document heading even though the hub owns the visible one;
- the `← {recipeName}` back link carries `aria-label="Back to {recipeName} {Overview|Live Runs}"`, derived from `parent`, so it announces its destination;
- `BotStageSubNav` is rendered with `currentMode="item"`;
- an optional `alerts` slot renders inline notices (live-switch confirmation, quota/execution errors, fork errors) under the sub-nav inside the scene, so a detail page whose panels own the action buttons never loses the feedback the hub card gives;
- the panel box is written out by hand — `relative z-10 mx-auto flex w-full max-w-[calc(80rem+3rem)] flex-col gap-6 px-6 pb-8 md:pb-12` — instead of `PageLayout maxWidth="xl"`, because `SceneStage` centres a `max-w-7xl` box inside its own `px-6` and a `PageLayout` preset would emit a competing `max-w-*` utility (`cn` is bare clsx, not tailwind-merge). See [[concepts/page-surface-conventions]].

#### `/build` — 3-Step Chat Builder (`BuilderChatPanel` → `BuilderAlignmentCard` → `CompiledBotWorkspace`)
- **Step 1 (Describe)**: `BuilderChatPanel` + `BuilderDescribeStep` + `BuilderStatusStrip` + `BuilderCompilePipeline` + `BuilderActivePrompt` + `BuilderMessageHistory` + `BuilderStepper` inside `SceneStage` (`CedarRidgeBackdrop` + `.scene-scrim .voxel-card`). No visible headline block — an `sr-only` `<h1>` carries the page name. The stage uses `build-stage-viewport` sizing and fluid `clamp()` gaps so the ridge band stays on screen below the card on a phone.
- **Step 2 (Align)**: `status: 'align'` renders `BuilderAlignmentCard` with 1 round of 3–5 tailored multiple-choice questions before compiling the final bot (`status: 'ok'`). Trading ideas with offline limits compile to `ok` with a `warning`; non-trading inputs stay `declined`.
- **Step 3 (Backtest & Go Live)**: `CompiledBotWorkspace` inside `PageLayout` over `GlobalBackground`. Its first block is `BuilderBotLiveStatus` for any saved bot, followed by `BuilderStatusStrip` (work axis), an in-flow `compiled-bot-live-warning` banner, `CompiledBotSummaryCard` (with recessed `compiled-bot-next-action` trough highlighting the primary CTA), and `BuilderStepper` (Step 3 active). **Save-then-navigate**: `handleSaveRecipe` persists an unsaved bot and then `navigate({ to: '/recipes/$recipeId', params: { recipeId: saved.id } })`; an already-saved bot stays put. Enabling live navigates to `/recipes/live/$recipeId/runs`. Empty-prompt guard disables Save/Backtest/live.
- Calm lower workspace (`CompiledBotBlueprintSection`) with a WAI-ARIA segmented tab bar (`Blocks & Tools` | `Prompt Preview`).

#### `/recipes` — My Bots Dashboard (`RecipeDashboardPage`)
- **Bot cards** (`BotCard`, fluid grid): the name link targets `/recipes/$recipeId` (Bot Overview) with an always-visible chevron; the live badge links to `/recipes/live/$recipeId/runs`; owner actions (Enable/Pause Live, Remove) plus a `+ Build New Bot` CTA to `/build`.
- **In-flight state**: the card derives the pending destination from the router via `pendingRecipeTarget(state.status, state.location)`, which now reports `workspace` for `/recipes/<id>` and `/recipes/<id>/edit` and `live` for `/recipes/live/<id>`. See [[concepts/state-machines]] §2.12.
- **Quota strip**, **Recent backtests strip**, **Alerts inbox**, **Waitlist pledge modal**.

#### `/recipes/$recipeId`, `/recipes/$recipeId/edit`, & `/recipes/live/$recipeId` — Split Bot Surfaces
- **`/recipes/$recipeId` (`RecipeOverviewPage`)**: Public-capable for `is_public`/`is_template` bots; `BotStageHeader` above 3 Matcha & Voxel blocks (Performance & Equity, Behaviors & Insights, Positions/Trades/Strategy DNA). Loads via `fetchRecipeOverviewFn` (30s bounded public cache).
- **`/recipes/$recipeId/performance` & `/recipes/$recipeId/behavior` (`RecipeOverviewDetailsPage`)**: public-capable detail tabs under `BotSceneShell` — `sr-only` `<h1>` from `sectionTitle`, sub-nav in `currentMode="item"`, and an `alerts` slot carrying `LiveSwitchConfirmation`, `StudioAlertSlot`, and the fork error. `WaitlistPledgeModal` mounts outside the shell.
- **`/recipes/$recipeId/edit` (`RecipeEditPage`)**: Owner-only Blueprint & Prompt Editor. Reached only by the owner; a non-owner renders an `ErrorCard`.
- **`/recipes/live/$recipeId` (`RecipeLivePage`)**: Public-capable; `BotStageHeader` (`TurboButton` for owners) above paginated `Live Run Traces`, embedded `Live Paper Portfolio`, and `All Closed Live Trades`.

#### `/recipes/backtest/$jobId` — Live Backtest View (`RecipeBacktestPage`)
- Polls `fetchRecipeRunDetailFn` every 1.5s
- Timeline, telemetry, portfolio, trades, session trace
- Header links: `← Bot Overview` → `/recipes/$recipeId` and `Edit Blueprint` → `/recipes/$recipeId/edit` (a `live_turn` job links to `/recipes/live/$recipeId/runs`)

#### `/recipes-demo` — Public Showcase
- Pinned backtest via `recipe_showcase` table (CLI `publish_showcase`)
- Read-only `RecipeBacktestPage` with `readOnlyShowcase` mode
- "Sign In Free to Build & Run" → `/build`

## 4. Behavioral Insights & Overview Metrics

The Bot Overview surface renders deterministic behavioral telemetry computed server-side from the recipe's live runs and closed trades:

- **`computeBotBehaviors`** (`apps/web/src/features/recipes/utils/recipe-insights.ts`): Aggregates action mix (BUY/EXIT/SELL/HOLD counts, hold selectivity), ticker focus (signal count, closed count, wins, net PnL), exit reasons, tool footprint, and the latest decision snapshot. Source is `live` when completed live turns exist, `backtest` when only backtest data is available, or `none` when neither exists.
- **`deriveOverviewMetrics`** (`apps/web/src/features/recipes/utils/overview-metrics.ts`): Computes top-level KPIs (total equity, cash, net return %, win rate, open positions) prioritizing live paper state and falling back to the latest completed backtest before live turns begin.
- **`BotBehaviorsBlock`**: Four equal-height recessed `.voxel-trough` panels (Action Mix & Selectivity, Ticker Focus & Exits, Tool Footprint, Latest Decision Snapshot) inside one `.voxel-card`. Its latest-decision panel links a `live_turn` decision to `/recipes/live/$recipeId/runs`.
- **`PerformanceOverviewBlock`**: KPI strip (Total Equity, Net Return, Cash Available, Win Rate, Open Positions) plus a `PerformanceChart` with benchmark overlay, bounded to the active portfolio date range.
- **`ClosedTradesSection`**: Closed trades ledger with in-flow `.voxel-trough` catalyst & confidence inspection (zero floating tooltips, full keyboard accessibility).

## 5. 5-Block Push-Based Model (`version: "2.0-push"`)
- Single LLM call per run (enforced at Studio UI, engine schema, scheduler, save API, fork API, builder compiler, DB constraint)
- Blocks: `output_format` (immutable, rendered last), `prompt` (required, rendered first), `news`, `memories`, `technicals`
- Starter templates in `packages/config/starter-recipes.json`

## 6. My Strategies: Soft-Hide (Never Delete)
- Removal = `archived_at` stamp + `is_live: false` + `turbo_expires_at: null` + cancel pending queue rows; `invalidatePublicRecipeCache(recipeId)` drops the public read caches
- `fetchUserRecipes` filters `.is('archived_at', null)`
- Restore only via explicit `saveRecipe({ restore: true })`
- Forking archived recipe refused

## 7. Public Read Caching & Invalidation

`fetchLivePortfolioAndRuns` and `fetchRecipeOverview` accept a nullable `userId`. Non-owner reads of public/template recipes are served from bounded 30-second in-memory caches (`publicLiveCache`, `publicOverviewCache`, max 50 entries, oldest-evicted); owner reads are never cached. `clearPublicRecipeReadCaches()` clears both (test/ops hook), and `invalidatePublicRecipeCache(recipeId)` drops a single recipe's entries on every save, archive, live toggle, live switch, and Turbo activation. `assertReadableRecipeRow` enforces that a non-owner can only read `is_public`/`is_template` rows and never an archived one, and `fetchRecipeOverview` strips the row `id` from the returned `strategy` for non-owners so the owner's `user_id` is never leaked.

## 8. Pausing Live Schedule
- `toggleLiveSchedule` clears `turbo_expires_at` and cancels pending `live_turn` rows; `invalidatePublicRecipeCache(recipeId)` drops the public read caches
- `strategy_recipes_turbo_requires_live` CHECK backstops

## 9. Fork (Copy Into Your Account)
- `forkRecipe` copies public/template/own recipe → new row owned by caller
- Strips live scheduling, publication, Turbo window
- Resets paper ledger to $10,000 cash
- **All user bots are public by default** (`is_public: true`)

## 10. Draft & Explicit Save (`useRecipeDraft`)
- `RecipeSaveState`: `idle` → `saving` → `saved` | `error`
- Revision guard (`draftRev`), flight-scoped `isSaving`, generation guard
- Save failures → inline `RecipeNameField` alert (not top slot)

## 11. 30-Minute Market-Hours Runner Daemon
- `due_trading_slot` aligns to 14 half-hour ET slots (Mon–Fri, excl. US holidays + Good Friday)
- `enqueue_live_recipes_with_stats` pages live recipes, skips recent-Turbo, validates single-stage
- `run_live_lane_tick`: due slot → Turbo enqueuer (throttled 30s) → always drain `live_turn`
- `drain_lane`: serial by default, `LIVE_TURN_CONCURRENCY=10` for live, `RECIPE_BACKTEST_CONCURRENCY=3` for backtest

## 12. Live News Sync
- `sync_live_news_to_corpus`: market wires (Alpaca/Polygon/FMP) + newsletter snapshots
- Idempotent upsert on `article_id`
- Throttled to 300s on Turbo ticks, unconditional on scheduled slots

## 13. Point-in-Time Backtesting
- Random 10-trading-day window, 3x/day ET slots (30 sessions)
- Strict PIT context via `fetch_push_context_batch` + `execute_pit_tool`
- Intraday pricing from `recipe_intraday_bars` → FMP → Alpaca → `price_history`
- Long-Only portfolio accounting with whole-share sizing

## 14. LLM Endpoint Failover (`llm_caller.py`)
- Ordered chain: OpenRouter (if key) → Strata → Free Proxy (`auto-go`)
- `filter_recipe_tool_names` drops `web_search`, non-canonical, and non-PIT tools in backtests
- `_sanitize_recipe_tool_args` clamps every LLM-supplied tool argument before dispatch
- `run_tool_loop`: 5 tool rounds + forced final synthesis

## 15. Worker Modes & Safety
- `JobOutcome`: `EMPTY` | `COMPLETED` | `FAILED`
- `SUPPORTED_JOB_MODES`: `backtest`, `live_turn`, `compile`
- No nested event loop (`async_process_next_recipe_job` awaits directly)

## 16. Stale Compile Guard (Claim-Time Refusal)
Compile jobs are protected against aging out between the sweep and the pop poll. `_execute_compile_job` re-reads `created_at` and raises `RuntimeError(STALE_COMPILE_MESSAGE)` when `(now − created_at) > STALE_COMPILE_SECONDS` (600s), **before** `consume_builder_compile` and before any provider call.

## 17. Public Recipe Surface
- `/` = Home CTA page
- `/lab` = 3-block directory
- `/build` = Primary builder entry (chat → workspace; `?recipeId=` redirects to `/recipes/$recipeId`)
- `/recipes` = Gallery (anonymous) / Dashboard (signed-in)
- `/recipes/$recipeId` = public-capable Bot Overview; `/recipes/$recipeId/edit` = owner Blueprint; `/recipes/live/$recipeId` = public-capable Live Runs (redirects to `/recipes/live/$recipeId/runs`)
- `/recipes-demo` = Pinned showcase backtest
- Materialised stats only (zero frontend compute)

## Related Pages
- [[entities/database]] — `recipe_*` / `strategy_recipes` tables, `activate_recipe_turbo` RPC, `pop_next_recipe_job`
- [[entities/recipe-live-status]] — dedicated live page and Turbo control
- [[entities/secondary-minipc-edge]] — hosts `recipe-worker` container
- [[concepts/recipe-turbo-mode]] — 5-minute Turbo window, atomic RPC, market-hours helpers
- [[concepts/recipe-portfolio-engine]] — whole-share sizing, Alpaca paper mirror
- [[concepts/recipe-backtest-concurrency]] — counted three-concurrent-backtest guard
- [[concepts/recipe-public-stats]] — materialised public board and desk tables
- [[concepts/recipe-ops-telemetry]] — durable scheduler telemetry
- [[concepts/recipe-builder-usage]] — per-user daily compile metering
- [[concepts/recipe-builder-compiler]] — plain-English → Push v2 compiler behind `/build`
- [[concepts/atomic-live-schedule-switch]] — the live switch and public-cache invalidation
- [[concepts/page-surface-conventions]] — hub/detail chip `aria-current` modes, the `sr-only` detail `<h1>`, and the hand-written shell box
- [[concepts/fluent-responsive-design]] — the intrinsic `BotSummaryStrip` grid
- [[entities/free-llm-proxy]]
- [[entities/design-system]]
- [[concepts/zero-frontend-compute]]
- [[concepts/zero-lookahead-materialization]]
- [[concepts/state-machines]] — `RecipeJobStatus`, `RecipeSaveState`, `BacktestError`, `LiveScheduleState`
- `packages/config/recipe-naming.json` — shared naming contract
