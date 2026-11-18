---
tags: [recipes, push-v2, live, status, paper-portfolio, timezone]
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
- **Live Run Traces** — `RunSelectorBar` of the last 10 persisted `live_turn` jobs, each rendering stage prompt, per-round reasoning, tool calls & results, and full output through `TraceInspectorBlock`. Each stage header uses the fixed `LLM Call` label (no per-stage title). There is no inline `Latest Turn` option — the studio no longer runs live turns inline, so only persisted daemon runs appear here.
- **Empty / Error State** — if the recipe has no live runs yet, the page renders a quiet trough ("No live runs yet. The first scheduled run will execute at the next 3x/day ET slot (09:30, 12:30, 15:30)."). If the loader fails soft, the page renders the portfolio-less fallback without crashing.

## Eastern-Time Formatting (`America/New_York`)

Every timestamp on the page is rendered in Eastern time through `formatEasternDateTime` (`~/utils/date`), never as a raw UTC slice:

- **Run selector labels** — each `RunSelectorBar` button is labeled `formatEasternDateTime(run.created_at)` (e.g. `Apr 6 • 5:32 AM ET`). When `created_at` is missing or formats to `Unknown`, the label falls back to the first 8 characters of the run id so the button is never blank.
- **Active-run slot badge** — the badge shows `activeRun.slot_label` when the run recorded one, otherwise `formatEasternDateTime(activeRun.as_of_utc)` instead of the previous truncated UTC ISO string.

Both DST halves must be correct, so the conversion is driven by `Intl.DateTimeFormat` with `timeZone: 'America/New_York'` rather than a fixed UTC offset.

## Next-Run Label (`getNextSlotLabel`)

`getNextSlotLabel(now: Date)` derives the next scheduled slot from the real ET wall clock and returns either `<HH:MM> ET today` or `09:30 ET tomorrow` / `09:30 ET Monday`:

- It resolves the ET weekday, hour, and minute via `Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', weekday: 'short', hour: 'numeric', minute: 'numeric', hourCycle: 'h23' }).formatToParts(now)` — the previous implementation applied a hardcoded `-4` (EDT) offset, which was wrong for the whole EST half of the year.
- `Sat` / `Sun` → `09:30 ET Monday`.
- Otherwise the next slot is the first of `[9.5, 12.5, 15.5]` (09:30, 12:30, 15:30 ET) strictly greater than the current ET hour. A remaining slot renders as `<HH:MM> ET today`.
- If no slot remains today, `Fri` → `09:30 ET Monday` (the weekend has no sessions); any other weekday → `09:30 ET tomorrow`.

`RecipeLivePage.test.tsx` pins this behavior with fake timers across the boundaries: 15:50 EST Wednesday → `09:30 ET tomorrow`, 12:00 EST Wednesday → `12:30 ET today`, 16:00 EST Friday → `09:30 ET Monday`, and Saturday → `09:30 ET Monday`.

## Why a Separate Page

- **Studio separation of concerns**: `/recipes` is the configuration surface (templates, blocks, tools, save, backtest enqueue, live toggle). Live monitoring is observational and belongs elsewhere.
- **No polling**: the studio no longer polls for live turns. The daemon handles live execution on the 3x/day ET cadence, and the live page is refreshed by navigation or reload.
- **Max 1 live recipe**: enabling Scheduled Live while another recipe is live triggers `LiveSwitchConfirmation` (inline trough, not a modal) in the Studio. The switch disables the old recipe first, then enables the new one, then navigates here.

## Related

- [[entities/recipe-studio]] — studio architecture, draft/save state machine, `BacktestError`, `StudioAlertSlot`, live switch confirmation
- [[entities/secondary-minipc-edge]] — hosts the `recipe-worker` daemon that drains the `live_turn` lane with bounded concurrency
