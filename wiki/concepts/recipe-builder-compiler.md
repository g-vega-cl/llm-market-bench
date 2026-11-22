---
tags: [recipes, builder, llm, compiler, validation, fallback, local-draft]
category: concept
---

# Recipe Builder Compiler

The **Recipe Builder Compiler** turns a plain-English trading idea into a validated Push v2 recipe. It is the `/build` route's brain: `apps/web/src/features/recipes/builder/compiler.ts` (pure) plus `compile-queue.ts` (enqueue + poll server functions), with `BuilderChatPanel.tsx` (the chat panel mounted at `/build` and linked from `/lab`), `BuilderConversation.tsx`, and `use-builder-chat.ts` providing the UI and conversation state.

The guiding rule is that the model **never edits the graph freehand**. Whatever it returns is re-validated against the same contracts the studio, the save API, the scheduler, and the database enforce, and an unbuildable or twice-invalid reply degrades to a runnable starter template rather than a dead end.

## Two Entry Points, One Panel

`BuilderChatPanel.tsx` is the single implementation of the chat builder. It is mounted at `/build` (primary) and linked from the homepage (`/`) and the public recipe gallery (`/recipes`). The panel accepts an optional `idea` seed and `userId`, and an optional `redirectTo` (default `/build`) used when an anonymous visitor is sent to sign in. Extracting the panel means the builder is discoverable from the lab directory without duplicating the conversation, metering, or draft-handoff logic.

## Capability Manifest

`capabilityManifest()` is generated from the real block and tool types (`CURATED_TOOLS`, `types.ts`), not from prose, so the model can never choose a block, tool, or field the engine would reject at run time:

- **Blocks** — `prompt`, `news`, `memories`, `technicals`, and the required `output_format` (always rendered last), each with its literal JSON shape.
- **Tools** — one line per curated tool. `web_search` is filtered out of the manifest, and the hard constraints state *Never use web_search* — every run is point-in-time and offline.
- **Hard constraints** — long only (`BUY`/`EXIT` or `[]`), exactly one stage (one LLM call per run), `cadence` must be `"3h"` (the scheduler ignores `5m`/`1d`), and every block/stage needs a unique short id.

`compilerSystemPrompt()` wraps the manifest with the three reply shapes and the interaction rules: at most one question per reply and at most two across a conversation, `ok` immediately when the idea is specific enough, and `declined` (plus the nearest buildable version in `closest`) when the idea needs shorts, options, leverage, intraday triggers, or live web search.

## Reply Shapes

`CompilerReply` is a discriminated union:

| Shape | Meaning |
| :--- | :--- |
| `{ status: 'ok', strategy, summary, fallback? }` | A validated single-stage recipe, ready for the Compiled Bot Workspace |
| `{ status: 'question', question, options }` | One clarifying question with up to `MAX_OPTIONS` (4) choice buttons |
| `{ status: 'declined', reason, closest? }` | The engine cannot express this idea; `closest` describes the nearest buildable version |

## Validation Chain (`validateStrategy`)

Validation runs the same checks in the same order the rest of the system would:

1. **Envelope** — `version` must be `2.0-push`, `name` must be non-empty, `cadence` must be exactly `3h`, and `stages` must be an array of length exactly one.
2. **Blocks** — every block needs a known `type` (`prompt`/`news`/`memories`/`technicals`/`output_format`) and a non-empty string `id`; `prompt` needs string `text`, `news` needs an array `contains` plus a finite `recency_hours`, and `technicals` needs an array `rules`. Anything else is `unknown or malformed block`.
3. **Block contract** — block ids must be unique, an `output_format` block must exist, it must be **last**, and a prompt block is capped at 4000 characters.
4. **Tools** — every `selected_tools` entry must exist in `CURATED_TOOLS` and must not be `web_search`.
5. **Shared invariants** — `assertSingleLlmStage()` and `assertNoPrevOutputPlaceholder()` from `recipes-validators.ts`, the same guards the save and fork APIs use.

The result is normalized (name trimmed and capped at 40 chars, description at 200) and typed as `PushStrategy`.

## Parsing (`parseCompilerReply`)

`stripFences()` removes a ```` ```json ```` wrapper if the model added one, then the payload is parsed as strict JSON. Prose instead of JSON throws, which is what lets the caller retry instead of silently accepting nothing. An `ok` reply whose strategy fails `validateStrategy` also throws.

## Degrade, Never Dead-End (`fallbackReply`)

`fallbackReply()` validates `STARTER_RECIPES[0]` through the same `validateStrategy` and returns it as an `ok` reply with `fallback: true`, so the visitor always leaves with a runnable bot. The UI renders that as a `CLOSEST WORKING TEMPLATE` badge instead of `RECIPE COMPILED`. It is applied in two places: automatically when a returned reply cannot be parsed as a recipe, and explicitly through the **Use closest template** button after a failed job.

## Queued Compile (`compile-queue.ts` + the recipes daemon)

Compiles are **not** executed inside the HTTP request. The edge severs a synchronous server function somewhere between a 27.8s success and a 30.1s Cloudflare `502 origin_bad_gateway`, and the free provider regularly needs longer, so `/build` enqueues a job instead:

- **Enqueue** (`enqueueCompileFn`, POST) — auth, then a cheap pre-check against `recipe_builder_usage` (blocks at `BUILDER_DAILY_LIMIT` 25 with the "come back tomorrow" copy) and a pending cap of `MAX_PENDING_COMPILES` (2) per user. It then inserts a `recipe_execution_queue` row with `mode='compile'`, `recipe_id=NULL`, and `payload_json = { model:'auto-go', temperature:0.2, messages: buildConversation(last 8 turns) }`. The prompt is built **server-side at enqueue time**, so the client never sees or shapes it.
- **Execute** — the 5s-poll daemon on the MiniPC (`apps/engine/recipes/runner.py`, `_compile_lane_loop`, concurrency 3) pops the row, spends one compile via `consume_builder_compile` **right before the provider call**, POSTs the stored body with a 60s timeout (`RECIPE_COMPILE_TIMEOUT_SECONDS`), and writes the raw reply to `result_json = { content }` (or `failed` + `error_message`).
- **Why the daemon stays dumb** — it never knows what a recipe is: the capability manifest, contract and validation live once, in TypeScript. Nothing about the model contract is duplicated in Python, so nothing can drift. The trade is a small, generic executor in the engine instead of a second compiler.
- **Poll** (`fetchCompileJobFn`, GET) — auth-scoped read of that row; `useBuilderChat` polls every 2s while the job is `pending`/`processing` and then parses the reply with `parseCompilerReply` + `isCompilerReply`.
- **Never a dead end** — an unparseable reply degrades to `fallbackReply`; a `failed` job shows its error plus **Try again** and **Use closest template** (an explicit action, no silent substitution).

The deployed web is useless without the daemon, so the rollout order is migration → replica PostgREST reload → daemon → web. See [[concepts/recipe-compile-queue]].

## Conversation Sanitization (`buildConversation`)

Client-supplied roles are filtered to `user`/`assistant` only and each turn is truncated to `MAX_TURN_CHARS` (2000) before the system prompt is prepended, so a crafted request cannot append its own system prompt after ours. `buildCompilePayload()` further caps the slice it stores at `MAX_MESSAGES` (8) turns.

## Client State & Anonymous Drafts (`useBuilderChat`)

- **State** — `messages`, parallel `messageIds` (stable React keys), `draft`, `reply`, `error`, `pendingIdea`, the polled `jobId`, plus the derived `phase` and `elapsedMs` the status strip renders.
- **Unknown payload is a failure, not a crash** — the Start client resolves a non-envelope response (edge 502, cut-off request) to `undefined` instead of throwing, so the poll wraps `fetchCompileJobFn` in `assertServerFnResult()` and sets a retryable message. `retry()` re-enqueues the last turn without appending a duplicate message.
- **Signed-out users** — `send()` stores the message via `savePendingIdea()` and calls `onNeedSignIn`, which navigates to `/auth?redirect=<redirectTo>` (the panel's `redirectTo` prop, default `/build`). The idea survives the redirect and is replayed from `localStorage`, so signing in never costs the visitor their idea.
- **Signed-in users** — enqueues the conversation via `enqueueCompileFn`, polls the job, appends the assistant's question to the transcript on a `question` reply, and on an `ok` reply:
  - Does **not** save a local draft (the compiled strategy flows directly into the Compiled Bot Workspace)
  - Calls `clearPendingIdea()`
- **Analytics** — `track(posthog, ...)` emits `builder_question_answered`, `builder_declined`, and `builder_compiled` (with the cadence), and `BuilderChatPanel` emits `builder_opened` with `seeded`. See `apps/web/src/lib/analytics.ts`.

## Compiled Bot Workspace (`CompiledBotWorkspace` + `CompiledBotSummaryCard`)

When compilation succeeds (`reply.status === 'ok'`), `BuilderChatPanel` renders `CompiledBotWorkspace` instead of the chat interface:

- **Summary card** (`CompiledBotSummaryCard`) — status badge, bot name, description, active block badges, tool count
- **Primary CTA** — "▶ Backtest (Random 2W)" (auto-saves → enqueues backtest → navigates to `/recipes/backtest/$jobId`)
- **Live toggle** — "Enable Live (30m)" / "Pause Live" with max-3-bots conflict confirmation (`LiveSwitchConfirmation`)
- **Turbo button** — 5m × 1h boost, 1/day per user, countdown label
- **Collapsible editor** — "Edit blocks & tools ▼" reveals `StageBuilder` (5 blocks, delete-only) + `ToolPicker` (no Select All/Clear)
- **Collapsible raw prompt** — "View raw prompt ▼" reveals `PromptVisualizer` with live data preview
- **"← My Bots" link** — returns to `/recipes` dashboard
- **Guidance links** — "Take our 10-question personality test" (`/personality`) and "talk to our AI advisor" (`/chat`)

## Always-On Status (`BuilderStatusStrip`)

`/build` renders one status line for its whole life — never only while a spinner spins — because a compile is a slow request and a silent screen is indistinguishable from a broken one:

- `BuilderChatPanel` mounts it above the header with the hook's `phase` and `elapsedMs`: `READY`, `SIGN IN TO BUILD`, `QUEUED` (waiting for the daemon), `COMPILING` (counting up), `YOUR ANSWER NEEDED`, `CANNOT RUN AS DESCRIBED`, `BOT READY`, `FAILED`. Only the label and text sit in the `role="status"` live region — the elapsed clock is `aria-hidden`, so a countdown does not queue one announcement per second.
- `CompiledBotWorkspace` uses the same component for the draft and for background work. Both axes stay visible (`Draft not saved yet · Last backtest finished`), because a settled run from last week must never hide an unsaved draft. The run itself comes from `useLatestRecipeRun`, which reads the newest job **for that recipe** (`fetchLatestRecipeRunFn`, index-aligned) through TanStack Query and sets `refetchInterval` only while it is `pending`/`processing` — a hidden tab pauses, a transport failure keeps the last good row, and one cache entry is shared.
- A failure also renders the message plus a `Try again` button wired to `retry()`, which re-runs the last turn under an `inFlight` latch so a double click cannot spend two metered compiles.

## Browser Draft Handoff (`utils/local-draft.ts`)

`recipe_draft:v1` holds `{ strategy, savedAt, source: 'builder' | 'studio' }`; `recipe_builder_pending:v1` holds the anonymous idea. Both reads/writes are SSR-guarded and `try/catch`-wrapped, so private-mode or full storage simply leaves the draft in memory. `loadLocalDraft()` rejects a stored draft whose `stages` is not exactly one element, so a malformed or legacy value is ignored rather than loaded.

`RecipeDashboardPage` (the `/recipes` dashboard) adopts the draft in a `useEffect` (never a state initializer — reading `localStorage` during render would make the first client paint differ from SSR), guarded by an `importedRef` and by the presence of `initialStrategy`, then calls `clearLocalDraft()`. A compiled recipe therefore opens in the dashboard exactly once.

## Tests

- `apps/web/src/features/recipes/builder/compiler.test.ts` — manifest, `validateStrategy`, `parseCompilerReply`, `fallbackReply`, `buildConversation`, `isCompilerReply`
- `apps/web/src/features/recipes/builder/compile-queue.test.ts` — payload shaping (system prompt first, 8-turn cap), the 25/day pre-check, the 2-pending cap, the inserted row shape, and a null poll
- `apps/web/src/features/recipes/builder/use-builder-chat.test.tsx` — enqueue → poll → question transcript, QUEUED phase, unparseable reply degrades to the template, failed job is retryable with no stale reply, envelope-less poll is legible, meter refusal, double-click latch, explicit template fallback, anonymous parking
- `apps/engine/recipes/test_worker.py` — compile jobs: meter before the provider call, daily-limit stop without a provider call, provider failure recorded, missing payload fails closed
- `apps/web/src/features/recipes/builder/BuilderStatusStrip.test.tsx` — always-mounted live region, clock kept out of the live region, slow-provider copy, failure copy, run-state override, wrap classes per design-spec §9
- `apps/web/src/features/recipes/builder/CompiledBotWorkspace.test.tsx` — default collapsed state, dirty unsaved bot enables Save and says so, running run surfaces with progress, a settled run never hides an unsaved draft, backtest flow auto-saves and navigates
- `apps/web/src/features/recipes/utils/local-draft.test.ts` — draft round-trip, malformed storage, non-single-stage draft, clearing, pending-idea save/load/clear

## Related

- [[entities/recipe-studio]] — the studio dashboard, live status page, and `/build` route
- [[concepts/recipe-builder-usage]] — the 25/day compile meter this flow spends
- [[concepts/state-machines]] — where `RecipeSaveState`, `BacktestError`, `LiveScheduleState` lifecycles are registered
- [[entities/free-llm-proxy]] — the `auto-go` endpoint the compiler calls
- [[concepts/zero-lookahead-materialization]] — why `web_search` is banned in recipes
