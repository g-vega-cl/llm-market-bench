---
tags: [recipes, push-v2, live, status, paper-portfolio]
category: entity
---

# Recipe Live Status Page (`/recipes/live/$recipeId`)

The dedicated live-status page for a Push v2 strategy. Previously live paper portfolio and run traces lived inline on the Studio (`/recipes`), which conflated configuration with live-run monitoring and forced the studio to poll for updates. The live view now has its own route, server-rendered through `RecipeLivePage`, so the studio stays a pure editor and the live page can focus on portfolio and run history without background polling or SSE.

## Route

- **File**: `apps/web/src/routes/_authed/recipes/live/$recipeId.tsx`
- **Loader**: `useLoaderData` seeds `RecipeLivePage` via `fetchLivePortfolioAndRunsFn({ data: { recipeId } })`. The call fails soft to `null`, so a missing or stale recipe never breaks the page.
- **Auth**: guarded like all `/_authed` routes; the loader redirects to login when the user is not signed in.

## Page Content

- **Header** — a `← Back to Studio` link, the `Live Status` heading, the short recipe id, a `Live: ON (3x/d)` success badge, and a `Next run: <slot>` label computed from the current ET time (`getNextSlotLabel`).
- **Live Paper Portfolio** — `RecipePortfolioBlock` fed by `paper_cash` / `paper_positions` / `paper_trades`, with every open position enriched by the latest mark price.
- **Live Run Traces** — `RunSelectorBar` of the last 10 persisted `live_turn` jobs (labeled by `created_at`), each rendering stage prompt, per-round reasoning, tool calls & results, and full output through `TraceInspectorBlock`. Each stage header uses the fixed `LLM Call` label (no per-stage title). There is no inline `Latest Turn` option — the studio no longer runs live turns inline, so only persisted daemon runs appear here.
- **Empty / Error State** — if the recipe has no live runs yet, the page renders a quiet trough ("No live runs yet. The first scheduled run will execute at the next 3x/day ET slot (09:30, 12:30, 15:30)."). If the loader fails soft, the page renders the portfolio-less fallback without crashing.

## Why a Separate Page

- **Studio separation of concerns**: `/recipes` is the configuration surface (templates, blocks, tools, save, backtest enqueue, live toggle). Live monitoring is observational and belongs elsewhere.
- **No polling**: the studio no longer polls for live turns. The daemon handles live execution on the 3x/day ET cadence, and the live page is refreshed by navigation or reload.
- **Max 1 live recipe**: enabling Scheduled Live while another recipe is live triggers `LiveSwitchConfirmation` (inline trough, not a modal) in the Studio. The switch disables the old recipe first, then enables the new one, then navigates here.

## Related

- [[entities/recipe-studio]] — studio architecture, draft/save state machine, `BacktestError`, `StudioAlertSlot`, live switch confirmation
- [[entities/secondary-minipc-edge]] — hosts the `recipe-worker` daemon that drains the `live_turn` lane with bounded concurrency
