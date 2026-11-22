---
tags: [recipes, builder, llm, compiler, validation, fallback, local-draft]
category: concept
---

# Recipe Builder Compiler

The **Recipe Builder Compiler** turns a plain-English trading idea into a validated Push v2 recipe. It is the `/build` route's brain: `apps/web/src/features/recipes/builder/compiler.ts` (pure) plus `compiler-api.ts` (server function), with `BuilderChatPanel.tsx` (the chat panel mounted at `/build` and linked from `/lab`), `BuilderConversation.tsx`, and `use-builder-chat.ts` providing the UI and conversation state.

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

`compileStrategy()` (`compiler-api.ts`) attempts the proxy call twice. On the second attempt it echoes the previous error plus a "return the strict JSON shape only" turn. If both attempts fail it returns `fallbackReply(...)`, which validates `STARTER_RECIPES[0]` through the same `validateStrategy` and returns it as an `ok` reply with `fallback: true`. The UI renders that as a `CLOSEST WORKING TEMPLATE` badge instead of `RECIPE COMPILED`.

## Server Function & Metering (`compileStrategyFn`)

- **Auth** — `getAuthServerClient().auth.getUser()`; a missing `user.id` throws `Unauthorized: sign in to build a recipe`.
- **Input** — the message array must be non-empty.
- **Metering** — `consume_builder_compile({ p_user })` atomically spends one of `BUILDER_DAILY_LIMIT` (25) daily compiles before any proxy tokens are spent; exceeding the limit throws a message pointing the user at editing an existing recipe. See [[concepts/recipe-builder-usage]].
- **Proxy call** — `POST {FREE_LLM_PROXY_URL}/chat/completions` with `model: 'auto-go'`, `temperature: 0.2`, and an `AbortSignal.timeout(45_000)` so a hung free-tier provider cannot hold the request handler open. The base URL defaults to `https://llm.clvg.uk/v1`; the bearer key comes from `FREE_PROXY_MASTER_KEY` (falling back to `STRATA_API_KEY`, then `local`).

## Conversation Sanitization (`buildConversation`)

Client-supplied roles are filtered to `user`/`assistant` only and each turn is truncated to `MAX_TURN_CHARS` (2000) before the system prompt is prepended, so a crafted request cannot append its own system prompt after ours. `compileStrategyFn` further caps the slice it sends at `MAX_MESSAGES` (8) turns.

## Client State & Anonymous Drafts (`useBuilderChat`)

- **State** — `messages`, parallel `messageIds` (stable React keys), `draft`, `reply`, `isCompiling`, `error`, and `pendingIdea`.
- **Signed-out users** — `send()` stores the message via `savePendingIdea()` and calls `onNeedSignIn`, which navigates to `/auth?redirect=<redirectTo>` (the panel's `redirectTo` prop, default `/build`). The idea survives the redirect and is replayed from `localStorage`, so signing in never costs the visitor their idea.
- **Signed-in users** — sends the conversation to `compileStrategyFn`, appends the assistant's question to the transcript on a `question` reply, and on an `ok` reply:
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

## Browser Draft Handoff (`utils/local-draft.ts`)

`recipe_draft:v1` holds `{ strategy, savedAt, source: 'builder' | 'studio' }`; `recipe_builder_pending:v1` holds the anonymous idea. Both reads/writes are SSR-guarded and `try/catch`-wrapped, so private-mode or full storage simply leaves the draft in memory. `loadLocalDraft()` rejects a stored draft whose `stages` is not exactly one element, so a malformed or legacy value is ignored rather than loaded.

`RecipeDashboardPage` (the `/recipes` dashboard) adopts the draft in a `useEffect` (never a state initializer — reading `localStorage` during render would make the first client paint differ from SSR), guarded by an `importedRef` and by the presence of `initialStrategy`, then calls `clearLocalDraft()`. A compiled recipe therefore opens in the dashboard exactly once.

## Tests

- `apps/web/src/features/recipes/builder/compiler.test.ts` — manifest, `validateStrategy`, `parseCompilerReply`, `fallbackReply`, `buildConversation`
- `apps/web/src/features/recipes/builder/CompiledBotWorkspace.test.tsx` — default collapsed state, dirty unsaved bot enables Save, backtest flow auto-saves and navigates
- `apps/web/src/features/recipes/utils/local-draft.test.ts` — draft round-trip, malformed storage, non-single-stage draft, clearing, pending-idea save/load/clear

## Related

- [[entities/recipe-studio]] — the studio dashboard, live status page, and `/build` route
- [[concepts/recipe-builder-usage]] — the 25/day compile meter this flow spends
- [[concepts/state-machines]] — where `RecipeSaveState`, `BacktestError`, `LiveScheduleState` lifecycles are registered
- [[entities/free-llm-proxy]] — the `auto-go` endpoint the compiler calls
- [[concepts/zero-lookahead-materialization]] — why `web_search` is banned in recipes
