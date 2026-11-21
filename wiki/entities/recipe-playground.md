---
tags: [web, playground, homepage, recipes, builder, webgl, launch]
category: entity
---

# Recipe Playground (Homepage Bot Builder)

`apps/web/src/features/playground/` is the homepage bot builder. `/` no longer opens on a leaderboard: it opens on a five-block editor where a visitor stacks blocks, optionally describes the idea in one line, and runs a backtest (or puts the bot live) without leaving the page. The public board moved to `/live-desk`.

## Page Composition

`HomePlaygroundPage` (`pages/HomePlaygroundPage.tsx`) renders three regions inside one `PageLayout`:

1. **Hero** — the headline, the four fact pills (`2 free backtests/day`, `3 live bots`, `0 lookahead`, `paper cash only`), the market-mood sentence, links to `/live-desk` and `/recipes-demo`, and the `VoxelWorld` canvas on the right.
2. **`RecipePlayground`** — the editor itself.
3. **`ProofStrip`** — one winner and one loser from the leaderboard, with the as-of date.

## Editor (`RecipePlayground.tsx`)

State: `stage` (a single `StrategyStage`), `name`, `scenarioId`, `live`, `busy`, `result`.

- **`BlockStack`** renders every block as an always-open `BlockCard` (the design spec bans collapsibles). Content blocks carry `↑` / `↓` / `Remove` controls; the `output_format` block is labelled `locked` and has none. `moveBlock` refuses any move across the terminal block, because the hydrator renders `output_format` last regardless of stored order.
- **`deriveTools(blocks)`** supplies the tool list the draft will call (`get_stock_quote` always; `get_technical_indicators` + `get_key_metrics` for a technicals block; `get_todays_news_menu` for news; `get_price_history` for a prompt). `run_stock_screener` and `web_search` are never derived — they are live-only.
- **`DescribeLine`** posts one line to `compileStrategyFn` and adopts the compiled graph. A degraded reply says a starter was loaded instead of passing it off as the visitor's idea (`interpretReply`).
- **`ScenarioRow`** offers the five starter recipes under visitor-facing labels (`Chip tariff momentum`, `Follow the desk`, `Cheap quality`, `Fade the crowd`, `Earnings surprises`); picking one replaces the draft.
- **`RunStrip`** is the single action: `Run backtest` (or `Sign in to run`), an `Also go live at the next slot` checkbox, the remaining-runs counter, the derived tool list, and the outcome line.
- **`RunRequestForm`** appears when the visitor is out of runs (or a launch was blocked by `daily-cap`), and submits one `run_requests` row per ET day.

## Launch (`api/launch-recipe.ts`, `lib/launch.ts`, `lib/launch-result.ts`)

`launchRecipeFn` is an auth-gated `createServerFn` that validates the draft client-side (one stage, unique block ids, exactly one `output_format`, no `{{prev_output}}`), normalizes block order, and calls the `launch_recipe` RPC with a SHA-256 idempotency key over `userId | ET date | live flag | canonical graph`. The canonical graph sorts blocks by id and tools alphabetically, so renaming two blocks cannot buy a second run.

`launch_recipe` (`supabase/migrations/20261120000200_launch_recipe_rpc.sql`) does the whole launch in one transaction under `pg_advisory_xact_lock(hashtextextended(user_id || ':' || idempotency_key, 0))`: it replays a previously recorded `ok` outcome from `recipe_launch_requests`, validates the graph shape (one stage, non-empty blocks, terminal `output_format`), locks the caller's `recipe_user_quotas` row `FOR UPDATE`, inserts the `strategy_recipes` row, applies the live state (denied when the live-bot cap is reached), checks the daily / concurrent / global-queue caps, and enqueues exactly one `backtest` job (`priority: 0` for the caller's first-ever backtest, else `10`). A refused launch deletes the recipe row and clears `is_live`, so a blocked run leaves nothing behind. A blocked outcome is deliberately **not** replayed — a concurrent-cap at 09:31 must be re-evaluated once the queue drains at 09:35.

`LaunchResult` is a discriminated union — `backtest`, `live-only`, `blocked` (`daily-cap` / `concurrent-cap` / `queue-full` / `live-cap`), `invalid`, `error` — and `launchMessage` is the only place that turns an outcome into copy. A blocked launch is reported as `Saved, but no run was queued`, never as a failure. `normalizeLaunchRow` checks every nullable RPC column before trusting it (the admin client is untyped), so a partial row can never be cast into the union.

## Run Requests (`api/run-requests.ts`)

`submitRunRequestFn` inserts one `run_requests` row per user per ET day (`UNIQUE (user_id, request_day)`); a duplicate submit is a `23505` the UI explains as `You already asked today — one request per day is enough.` rather than a duplicate row. A missing table (`PGRST205`) degrades to `Requests are not open yet — try again after the deploy.`

## Market Mood (`lib/mood.ts`)

`normalizeMood` collapses the latest `market_feeling` row into a tagged union: `fresh` (direction, confidence, label, asOf), `stale` (older than 36 hours, or an unparseable timestamp — direction forced to `NEUTRAL`), or `unknown` (no row, or an unrecognised direction). `moodSentence` always states the reading in words; `moodTone` only colours the world.

## Proof (`lib/proof.ts`)

`pickProof(leaderboard)` takes the top row and the board's own `worst` row — the homepage publishes both rather than picking a favourable subset client-side — plus `medianReturnPct`, `trackedCount`, `windowDays`, and the as-of date from the last series point (falling back to the SPY series).

## Voxel World (`components/VoxelWorld.tsx`, `lib/world-gl.ts`)

A dependency-free WebGL2 instanced renderer (40 × 30 boxes, isometric projection) that echoes the mood tone. It is decorative only: the canvas sits inside `aria-hidden="true"` and is `pointer-events-none`.

- **Deferred init** — the GL context is created inside `requestIdleCallback` (with a `setTimeout` fallback), so it never competes with first paint.
- **Graceful degradation** — a missing context, a shader/program failure, a thrown factory, or a lost context all set a `WorldFallbackReason` (`no-context` / `shader` / `program` / `throw` / `context-lost`), warn once, and leave a static CSS bar terrain (`data-testid="world-fallback"`) instead of an empty box.
- **Budget discipline** — the rAF loop stops on `document.visibilityState === 'hidden'`, after 60 s of no activity, when paused, and under `prefers-reduced-motion` (one frame is still painted). The drawing buffer is capped at 1600 px on its longest axis with a single DPR scale for both axes.
- **Pause control** — a `Pause the world` / `Resume the world` button carries `aria-pressed`.

## Analytics

`apps/web/src/lib/analytics.ts` gains `playground_run`, `playground_run_blocked`, `playground_preset_applied`, `playground_describe_used`, `playground_describe_failed`, and `describe_it_failed`.

## Tests

`RecipePlayground.test.tsx` pins the always-open block editors, the derived tool list, scenario adoption, the anonymous sign-in redirect, and the absence of a move control on the answer block. `HomePlaygroundPage.test.tsx` pins the builder-first heading, the mood sentence, the published loser, and the request form appearing only at zero runs. `blocks.test.ts`, `describe.test.ts`, `launch-result.test.ts`, `mood.test.ts`, `proof.test.ts`, and `VoxelWorld.test.tsx` cover the pure helpers and every GL fallback path.

## Related

- [[entities/web-app]] — the dashboard that hosts `/` and `/live-desk`
- [[entities/recipe-studio]] — the full studio, the `launch_recipe` RPC, and the block contract
- [[concepts/recipe-builder-compiler]] — the plain-English compiler `DescribeLine` calls
- [[concepts/recipe-public-stats]] — the materialised board the proof strip reads
- [[concepts/portfolio-leaderboard-view]] — the leaderboard lanes rendered on `/live-desk`
- [[concepts/deploy-skew-payload-tolerance]] — the loader-boundary normalization this page relies on
