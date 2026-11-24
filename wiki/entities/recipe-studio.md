---
tags: [recipes, push-v2, trading, backtest, news-corpus, voxel, studio]
category: entity
---

# Recipe Studio

The **Recipe Studio** is now a two-surface experience:

1. **`/build` — The Chat Builder** (primary entry point)
   - Steps 1–2 render on the design-system `SceneStage` (`variant="hero"`, `motionRole="reactive"`) over the panoramic `GardenBackdrop` Cedar Sanctuary diorama with `SceneHudControls`, inside a `.scene-scrim .voxel-card` (no opaque `bg-voxel-canvas` or `GlobalBackground`)
   - Action-first ordering (§4b): visitors immediately see the compact `STEP 1 · NOW` status strip and auto-expansible `<textarea>` + `Continue to Alignment →` CTA at the top, with one-tap starter chips and `BuilderStepper` (`1. Describe` → `2. Align` → `3. Backtest & Go Live`) below
   - Compiles into a validated Push v2 recipe (one LLM call, point-in-time news, paper cash) with a real-phase `BuilderCompilePipeline` (`1. Queue` / `2. Model` / `3. Validate`)
   - Step 2 presents one round of 3–5 tailored multiple-choice alignment questions (`BuilderAlignmentCard`) before compiling the final bot
   - On success, shows a **Compiled Bot Workspace** summary `.voxel-card` inside `PageLayout` over `GlobalBackground`, with a single primary CTA: "▶ Backtest (Random 2W)" and a calm lower workspace switching between `Blocks & Tools` and `Prompt Preview`
   - Accessible from `/lab` directory and the homepage CTA

2. **`/recipes` — My Bots Dashboard** (signed-in users only)
   - Lists the user's saved strategies with minimal per-bot cards
   - Primary CTA: "+ Build New Bot" → `/build`
   - Each bot links to `/build?recipeId=<id>` for editing and `/recipes/live/$recipeId` for live monitoring
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
- `push_hydrator.py`: Point-in-time filtering and stage prompt hydration. Renders `prompt` blocks first, data blocks in the middle, and `output_format` blocks last so instructions lead the prompt and the schema lock is always final, regardless of block order in the stage.
- `portfolio_engine.py`: Shared Long-Only simulator (`PortfolioState`, `apply_portfolio_step`), whole-share sizing, Alpaca mirror
- `intraday_bars.py`: 3x/day ET slot expansion for backtests, live slot capture
- `pit_tools.py`: Strict point-in-time tool dispatcher for backtests
- `llm_caller.py`: Extracted LLM failover caller (`auto-go` → free proxy, no Strata contention)
- `push_runner.py` & `backtest_accounting.py`: Single-call live execution and 10-day backtests
- `worker.py`: `async_process_next_recipe_job` with optimistic CAS persistence
- `runner.py`: MiniPC dual-lane daemon (30m live slots + 5m Turbo + 5s queue poll)
- `public_stats.py`: Rebuilds materialised board tables after each lane drain
- `news_corpus.py`: Live news sync from market wires + newsletter snapshots

### 3. Presentation — Two Surfaces

#### `/build` — 3-Step Chat Builder (`BuilderChatPanel` → `BuilderAlignmentCard` → `CompiledBotWorkspace`)
- **Step 1 (Describe)**: Conversational builder (`BuilderChatPanel` + `BuilderDescribeStep` + `BuilderStatusStrip` + `BuilderCompilePipeline` + `BuilderActivePrompt` + `BuilderMessageHistory` + `BuilderStepper`) inside `SceneStage` (`GardenBackdrop` + `.scene-scrim .voxel-card`)
  - No visible headline block — the page name comes from the route `<title>` plus exactly one `sr-only` `<h1>` ("Build a trading bot from one sentence"), rendered by `BuilderChatPanel` for Steps 1–2 and by `CompiledBotWorkspace` for Step 3; a single `.voxel-card` with recessed `.voxel-trough` slots (zero nested `.voxel-card`)
  - Primary input & CTA front and center: `BuilderStatusStrip` (`STEP 1 · NOW`), any active prompt/error (`BuilderActivePrompt` / `BuilderErrorBanner`), and the auto-expansible `<textarea>` (`maxLength={2000}`, `Enter` for newline, `Ctrl/Cmd+Enter` to submit) + `Continue to Alignment →` hero CTA sit at the top; starter idea chips (`builder-starter-chips`), earlier message history, guidance links, and `BuilderStepper` sit below
  - Compiles via `enqueueCompileFn` / `fetchCompileJobFn` (25/day quota, `auto-go` model)
- **Step 2 (Align)**: `status: 'align'` renders `BuilderAlignmentCard` with 1 round of 3–5 tailored multiple-choice questions (clickable pills + optional custom input, `Skip & build with defaults`, and `Build Final Bot →` hero CTA) above `BuilderStepper` before compiling the final bot (`status: 'ok'`).
  - Only non-trading inputs stay `declined`; trading ideas with offline limits compile to `status: 'ok'` with a `warning` advising Live execution (and any stray trading `declined` reply is promoted automatically via `promoteDeclinedToBot()`)
  - Guidance links: `"Take our 16-question personality test"` (`/personality`, derived from `PERSONALITY_QUESTIONS.length`) and `"talk to our AI advisor"` (`/chat`)

- **Step 3 (Backtest & Go Live)**: **Compiled Bot Workspace** (`CompiledBotWorkspace` + `CompiledBotSummaryCard` + `CompiledBotBlueprintSection`) inside `PageLayout` over `GlobalBackground`
  - Centered `.voxel-card` summary holding single `BuilderStatusStrip` (owning the single `BOT READY` / `SAVED BOT` / `LIVE RECOMMENDED` / `CLOSEST WORKING TEMPLATE` / `PROMPT NEEDED` / active backtest badge), an in-flow `compiled-bot-live-warning` `.voxel-trough` banner whenever a compile `warning` or `liveOnly` tool (`LIVE_ONLY_TOOL_NAMES`) is active, `CompiledBotSummaryCard` (bot name `RecipeNameField`, summary, block/tool badges, and recessed `compiled-bot-next-action` trough highlighting `"▶ Backtest (Random 2W)"` or `"Enable Live (30m)"` alongside `LiveSwitchConfirmation`), and `BuilderStepper` (Step 3 active) below the summary CTAs
  - Empty-prompt guard: a blank `prompt` block renders `PROMPT NEEDED` and disables Save, Backtest, and the live toggle
  - Calm lower workspace (`CompiledBotBlueprintSection`) below the summary card with a WAI-ARIA segmented `.voxel-trough` tab bar (`Blocks & Tools` default via `StageBuilder` pinning the single editable `prompt` block first | `Prompt Preview` via `PromptVisualizer`), keyboard-navigable with ArrowLeft/ArrowRight/Home/End
  - "← Describe a different bot" or "← My Bots" link back to dashboard

#### `/recipes` — My Bots Dashboard (`RecipeDashboardPage`)
- **Empty state**: Hero card with "Build Your First Bot →" linking to `/build`
- **Bot cards** (`BotCard`, fluid grid, `minmax(min(100%,20rem),1fr)`):
  - Bot name → `/build?recipeId=<id>`, followed by an always-visible chevron that turns gold and nudges right on hover (`group/open`), plus a gold underline on hover/focus — the name alone read as static text on touch, where no hover state exists; the link carries `aria-label="<name> (open recipe workspace)"` so the affordance is not visual-only
  - In-flight state: the card derives the pending destination from the router (`useRouterState` + `pendingRecipeTarget(state.status, state.location)`, which reports `workspace` or `live`) rather than latching a local flag, then dims the name, swaps the chevron for the pulsing pending pixel in a fixed `w-4 h-4` slot, renders a `role="status"` line naming the destination ("Opening bot…" / "Opening live view…"), sets `aria-busy` on the actions row only (never on an ancestor of the live region), and drops both links' `href` plus disables both actions. A same-frame second click is prevented by reading `router.state.status` synchronously inside the click handler — no private latch to strand — and modified/aux clicks are never swallowed. Only the card being opened goes busy; siblings stay interactive. See [[concepts/state-machines]] §2.12
  - The two buttons — and the header "Build New Bot" link — stay locked for the duration of a live-toggle or removal mutation, so navigating away cannot discard that request's in-flow success or error message
  - Live badge ("LIVE 30m" success / "TURBO 5m" accent) → `/recipes/live/$recipeId` (goes inert with the rest of the card while opening)
  - "Enable Live (30m)" / "Pause Live" button (shared `useLiveScheduleControl` state machine)
  - "Remove" button (soft-hide via `archived_at`, never `DELETE`)
- **Quota strip** (`RecipeQuotaStrip`): Compact 1-line summary (backtests left, live bots, global queue)
- **Recent backtests strip** (`RecentBacktestsStrip`): Up to 5 `voxel-btn` links to `/recipes/backtest/$jobId`
- **Alerts inbox** (`RecipeAlertsInbox`): In-app trade alerts with "Mark Read"
- **Waitlist pledge modal** for capacity requests

#### `/recipes/live/$recipeId` — Live Status Page (`RecipeLivePage`)
- SSR via `fetchLivePortfolioAndRunsFn`
- Header: "← Edit Bot" → `/build?recipeId=<id>`, live badge, next run label, Turbo button
- Live paper portfolio (`RecipePortfolioBlock` with mark prices)
- Live run traces (`RunSelectorBar` + `TraceInspectorBlock`)

#### `/recipes/backtest/$jobId` — Live Backtest View (`RecipeBacktestPage`)
- Polls `fetchRecipeRunDetailFn` every 1.5s
- Timeline (`BacktestTimelineBlock`), telemetry (`BacktestTelemetryBlock`), portfolio, trades, session trace
- "Edit Bot" link → `/build?recipeId=<id>`

#### `/recipes-demo` — Public Showcase
- Pinned backtest via `recipe_showcase` table (CLI `publish_showcase`)
- Read-only `RecipeBacktestPage` with `readOnlyShowcase` mode
- "Sign In Free to Build & Run" → `/build`

### 5-Block Push-Based Model (`version: "2.0-push"`)
- Single LLM call per run (enforced at Studio UI, engine schema, scheduler, save API, fork API, builder compiler, DB constraint)
- Blocks: `output_format` (immutable, rendered last), `prompt` (required, rendered first), `news`, `memories`, `technicals`
- Starter templates in `packages/config/starter-recipes.json` (5 templates, all `cadence: "3h"`)

### My Strategies: Soft-Hide (Never Delete)
- Removal = `archived_at` stamp + `is_live: false` + `turbo_expires_at: null` + cancel pending queue rows
- `fetchUserRecipes` filters `.is('archived_at', null)`
- Restore only via explicit `saveRecipe({ restore: true })` from header "Save Recipe" button
- Forking archived recipe refused

### Pausing Live Schedule
- `toggleLiveSchedule` clears `turbo_expires_at` and cancels pending `live_turn` rows
- `strategy_recipes_turbo_requires_live` CHECK backstops

### Fork (Copy Into Your Account)
- `forkRecipe` copies public/template/own recipe → new row owned by caller
- Strips live scheduling, publication, Turbo window
- Resets paper ledger to $10,000 cash

### Draft & Explicit Save (`useRecipeDraft`)
- `RecipeSaveState`: `idle` → `saving` → `saved` | `error`
- Revision guard (`draftRev`), flight-scoped `isSaving`, generation guard
- Save failures → inline `RecipeNameField` alert (not top slot)

### 30-Minute Market-Hours Runner Daemon
- `due_trading_slot` aligns to 14 half-hour ET slots (Mon–Fri, excl. US holidays + Good Friday)
- `enqueue_live_recipes_with_stats` pages live recipes, skips recent-Turbo, validates single-stage
- `run_live_lane_tick`: due slot → Turbo enqueuer (throttled 30s) → always drain `live_turn`
- `drain_lane`: serial by default, `LIVE_TURN_CONCURRENCY=10` for live, `RECIPE_BACKTEST_CONCURRENCY=3` for backtest
- `run_hourly_cycle`: news sync → public stats → enqueue → drain

### Live News Sync
- `sync_live_news_to_corpus`: market wires (Alpaca/Polygon/FMP) + newsletter snapshots
- Idempotent upsert on `article_id` (`source_id_hash` for wires, `nl_<clean>_<date>` for newsletters)
- Throttled to 300s on Turbo ticks, unconditional on scheduled slots

### Point-in-Time Backtesting
- Random 10-trading-day window, 3x/day ET slots (30 sessions)
- Strict PIT context via `fetch_push_context_batch` + `execute_pit_tool`
- Intraday pricing from `recipe_intraday_bars` → FMP → Alpaca → `price_history`
- Long-Only portfolio accounting with whole-share sizing

### LLM Endpoint Failover (`llm_caller.py`)
- Ordered chain: OpenRouter (if key) → Strata → Free Proxy (`auto-go`)
- `filter_recipe_tool_names` drops `web_search`, non-canonical, and non-PIT tools in backtests
- `_sanitize_recipe_tool_args` clamps every LLM-supplied tool argument before dispatch: `get_market_moving_news` is forced to `force_refresh: false` (a prompt cannot bypass the 15m cache and trigger 10 Jev LLM calls per turn), and any numeric `limit` is clamped to `1.._MAX_RECIPE_TOOL_LIMIT` (25), bounding Recipe Studio query and LLM blast radius
- `run_tool_loop`: 5 tool rounds + forced final synthesis
- Both lanes resolve `auto-go` (no Strata contention)

### Worker Modes & Safety
- `JobOutcome`: `EMPTY` | `COMPLETED` | `FAILED`
- `SUPPORTED_JOB_MODES`: `backtest`, `live_turn`, `compile`
- No nested event loop (`async_process_next_recipe_job` awaits directly)
- Successful jobs: write `result_json`, increment `trial_count`, deposit `live_turn` alerts

### Stale Compile Guard (Claim-Time Refusal)
Compile jobs are protected against aging out between the sweep and the pop poll. The sweep (`fail_stale_compile_jobs`) marks unclaimed `pending` compile rows failed once they exceed `STALE_COMPILE_SECONDS` (600s) and releases the per-user cap, but the pop poll runs every 5s while the sweep runs only once a minute — so a row that aged past the window could still be claimed first.

`_execute_compile_job` therefore re-reads the row's `created_at` (selected alongside `payload_json, user_id`), parses it with `_parse_iso_utc` (tolerant of `Z` suffixes and naive timestamps, which are assumed UTC), and raises `RuntimeError(STALE_COMPILE_MESSAGE)` when `(now − created_at) > STALE_COMPILE_SECONDS`. The refusal happens **before** `consume_builder_compile` is called and before any provider tokens are spent, so a user is never charged for a stale row. The job is marked `failed` with `error_message = STALE_COMPILE_MESSAGE` ("The worker never picked this compile up. Try again."). Pinned by `test_compile_job_refuses_a_row_that_aged_past_the_window`, which asserts only `pop_next_recipe_job` is called (no meter RPC, no provider POST) and the row is failed with the stale message.

### Public Recipe Surface
- `/` = Home CTA page (headline + "Start building" → `/lab`)
- `/lab` = 3-block directory (My Bots, Investing Style, Research Engines, Audits)
- `/build` = Primary builder entry (chat → workspace)
- `/recipes` = Gallery (anonymous) / Dashboard (signed-in)
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
- [[entities/free-llm-proxy]]
- [[entities/design-system]]
- [[concepts/zero-frontend-compute]]
- [[concepts/zero-lookahead-materialization]]
- [[concepts/state-machines]] — `RecipeJobStatus`, `RecipeSaveState`, `BacktestError`, `LiveScheduleState`
- `packages/config/recipe-naming.json` — shared naming contract
