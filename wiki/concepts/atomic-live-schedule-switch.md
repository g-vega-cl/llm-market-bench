---
tags: [recipes, live, scheduling, rpc, atomicity, database, state-machine]
category: concept
---

# Atomic Live Schedule Switch

Enabling a recipe's 30-minute live schedule while another recipe is already live used to be a two-call client sequence: `toggleLiveScheduleFn({ isLive: false })` on the old recipe, then `toggleLiveScheduleFn({ isLive: true })` on the new one. That sequence is not atomic — a failure between the two calls leaves the user with **zero** live bots, the UI has to optimistically patch the old row to hide the gap, and the intermediate state can trip the 3-live cap. The switch is now a single `SECURITY DEFINER` RPC, `switch_live_schedule`, invoked through `switchLiveScheduleFn` and driven by the shared `useLiveScheduleControl` hook.

## The RPC (`supabase/migrations/20261124000000_switch_live_schedule_rpc.sql`)

```sql
switch_live_schedule(p_user_id UUID, p_pause_recipe_id UUID, p_enable_recipe_id UUID)
  RETURNS TABLE (paused_id UUID, enabled_id UUID, is_live BOOLEAN)
```

`SECURITY DEFINER`, `SET search_path = public`, `EXECUTE` revoked from `PUBLIC`/`anon`/`authenticated` and granted only to `service_role`.

In one transaction it:

1. rejects a missing argument and `p_pause_recipe_id = p_enable_recipe_id` (`Cannot switch a live bot with itself.`);
2. locks **both** `strategy_recipes` rows `FOR UPDATE` in deterministic UUID order (`LEAST` / `GREATEST` of the two ids) so two concurrent switches can never deadlock;
3. verifies both rows exist and are owned by `p_user_id` (`Unauthorized: cannot modify live schedule for another user`);
4. rejects an archived target (`This strategy was removed from My Strategies. Save it to restore before scheduling it live.`);
5. counts the user's *other* live recipes (excluding both ids) against `recipe_user_quotas.max_live_recipes` (default 3) and raises `Scheduled live limit reached (N/M). Pause an existing live recipe first.` when the cap would be exceeded;
6. pauses the old recipe — `is_live = FALSE`, `turbo_expires_at = NULL`, `updated_at = NOW()`;
7. cancels that recipe's `pending` `live_turn` queue rows (`status = 'cancelled'`, `cancelled_at = NOW()`);
8. enables the target — `is_live = TRUE`, `updated_at = NOW()`;
9. returns `(p_pause_recipe_id, p_enable_recipe_id, TRUE)`.

Because the pause, the queue cancellation, and the enable commit together, there is no window in which the user has no live bot, and the paused recipe can never keep a Turbo window or a queued live turn alive. See [[concepts/recipe-turbo-mode]].

## Server Function (`apps/web/src/features/recipes/api/recipes-quota-api.ts`)

`switchLiveSchedule(pauseRecipeId, enableRecipeId, userId)` pre-validates before touching the RPC, so the common failures never reach Postgres:

- reads `id, user_id, archived_at, graph_json` for the **target** recipe and throws `Recipe not found: <id>` when absent;
- throws `Unauthorized: cannot modify live schedule for another user` on an ownership mismatch;
- throws the archived-recipe message when `archived_at` is set;
- runs `assertSingleLlmStage()` and `assertNoPrevOutputPlaceholder()` on the target's `graph_json` — the same guards the save and fork APIs use;
- calls `db.rpc('switch_live_schedule', { p_user_id, p_pause_recipe_id, p_enable_recipe_id })` and throws `error.message` on failure;
- normalizes the `TABLE` result (array or single object) and throws `Failed switching live schedule: empty response` when `paused_id` / `enabled_id` are missing, returning `{ pausedId, enabledId, is_live }`.

After a successful switch it calls `invalidatePublicRecipeCache(pausedId)` and `invalidatePublicRecipeCache(enabledId)` so the public Bot Overview and Live Runs read caches (see [[entities/recipe-studio]] §7) never serve a stale `is_live` / `turbo_expires_at` for either recipe. `toggleLiveSchedule` and `activateRecipeTurbo` invalidate the same cache for their recipe id, and `saveRecipe` / `archiveRecipe` invalidate it too, so every mutation that changes what a public bot exposes drops its cached read.

`switchLiveScheduleFn` is the auth-gated `createServerFn({ method: 'POST' })` wrapper: it resolves the caller from `getAuthServerClient().auth.getUser()`, throws `Unauthorized: please sign in to manage live schedules` when there is no session, and passes the caller's `user.id` as `p_user_id` — the client never supplies its own identity.

## Client State Machine (`useLiveScheduleControl`)

`apps/web/src/features/recipes/utils/use-live-schedule-control.ts` is the single implementation shared by the studio (`/recipes`), the compiled bot workspace (`/build` Step 3), the Bot Overview (`/recipes/$recipeId`), the Blueprint editor (`/recipes/$recipeId/edit`), and the live page (`/recipes/live/$recipeId`) via `useBotHeaderActions`.

```ts
type LiveScheduleState =
    | { kind: 'idle' }
    | { kind: 'toggling'; recipeId: string }
    | { kind: 'confirming'; target: RecipeSummaryItem; conflicting: RecipeSummaryItem }
    | { kind: 'switching'; target: RecipeSummaryItem; conflicting: RecipeSummaryItem };
```

- **`toggle(target, persistFirst?)`** — a plain pause or enable. When enabling and `userRecipes.filter(r => r.is_live && r.id !== target.id).length >= maxLiveRecipes`, it parks in `confirming` instead of calling the API. Otherwise it persists the target first (`persistFirst`), resolves the recipe id (`saved?.id ?? target.id`, throwing `Could not determine strategy ID to enable/pause live schedule.` when neither exists), calls `toggleLiveScheduleFn`, patches `userRecipes` through `upsertSavedRecipeSummary` (or an in-place `is_live` / `turbo_expires_at` patch when nothing was saved), and navigates to `/recipes/live/$recipeId` only when the recipe was just enabled.
- **`confirmSwitch(persistFirst?)`** — moves `confirming` → `switching` (carrying both `target` and `conflicting`), persists the target, then calls `switchLiveScheduleFn({ pauseRecipeId: conflicting.id, enableRecipeId })`. On success it clears the old row's `is_live` and `turbo_expires_at`, upserts the saved target, returns to `idle`, and navigates to the new live page. On failure it sets `scheduleError` and returns to `idle` — never back to `confirming`.
- **`cancelSwitch()`** — `confirming`/`switching` → `idle`.
- **`isBusy`** — `toggling` or `switching`; the single mutual-exclusion latch the studio and `useBotHeaderActions` also use to block Backtest, Save, and Turbo.

### Save-before-switch ordering

The target is always persisted **before** the switch RPC. A failed save therefore throws out of `persistTargetId` and the RPC is never called, so the existing live bot is never paused for a replacement that does not exist. `CompiledBotWorkspace.test.tsx` pins this: a rejected `saveRecipeFn` during `confirmSwitch` surfaces one `role="alert"` and asserts `switchLiveScheduleFn` and `toggleLiveScheduleFn` were both never called.

### Envelope guarding and single-alert discipline

Every server-function result on this path goes through `assertServerFnResult()` (`~/lib/server-fn`) — `saveRecipeFn`, `enqueueRecipeJobFn`, `toggleLiveScheduleFn`, `switchLiveScheduleFn`, and `activateRecipeTurboFn` — so an envelope-less edge response becomes a legible error instead of a `TypeError` on `undefined`. `applyScheduleError` logs quota refusals at `warn` and everything else at `error`, and the studio/workspace/Bot-Stage header suppress the inline `RecipeNameField` save error whenever a backtest or schedule error is present, so exactly one alert renders.

## Presentation

`LiveSwitchConfirmation` renders for **both** `confirming` and `switching`, with `isSwitching={state.kind === 'switching'}` disabling the `Switch to This` button and setting `aria-busy="true"` while the RPC is in flight. In `BotStageHeader` the confirmation trough sits below the title/action row and above the sub-nav, so the primary CTA stays at the top of the card per [[concepts/page-surface-conventions]] §4b. The live toggle button reports in-flight state through its label — `Enabling Live...` / `Pausing Live...`.

## Tests

- `apps/web/src/features/recipes/builder/CompiledBotWorkspace.test.tsx` — save → enable live → `Enabling Live...` (disabled) → navigate to `/recipes/live/$recipeId`; a failed save surfaces exactly one `role="alert"` and never calls the toggle; `confirmSwitch` keeps `LiveSwitchConfirmation` visible with `aria-busy` and calls `switchLiveScheduleFn` once with `{ pauseRecipeId, enableRecipeId }`; a rejected save during `confirmSwitch` never pauses the existing live bot.
- `apps/web/src/features/recipes/pages/RecipeStudioPage.runs.test.tsx` — the conflict flow calls `switchLiveScheduleFn` **once** (not two `toggleLiveScheduleFn` calls) and navigates to the new live page.
- `apps/web/src/features/recipes/pages/RecipeDashboardPage.test.tsx` — mocks `switchLiveScheduleFn` alongside `toggleLiveScheduleFn` for the shared hook.

## Related

- [[entities/recipe-studio]] — the studio, Bot Overview, Blueprint, and `/build` workspace that host the switch
- [[entities/recipe-live-status]] — the live page the switch navigates to
- [[concepts/recipe-turbo-mode]] — the Turbo window cleared by the pause half of the switch
- [[concepts/state-machines]] — `LiveScheduleState` registry entry
- [[concepts/page-surface-conventions]] — primary-action ordering that keeps the confirmation trough below the summary card
- [[entities/database]] — `strategy_recipes`, `recipe_execution_queue`, `recipe_user_quotas`
