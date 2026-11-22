---
tags: [state-machines, architecture, fsm, verification, type-safety, state-minimization]
category: concept
---

# State Machines & State Space Minimization

This page serves as the canonical registry of explicit and implicit finite state machines (FSMs) across the backend engine, database, proxy services, and web frontend. It defines the valid discrete states, allowed transitions, transition guards, and catalogs implicit multi-boolean/nullable combinations targeted for systematic collapse into explicit types.

---

## 1. Core Principles of State Space Minimization

Systems with unconstrained state suffer from combinatorial explosion ($2^N$ states for $N$ boolean flags) and implicit edge states that evade unit tests. When designing or refactoring systems:

1. **Eliminate Boolean Flag Sprawl**: Never combine multiple boolean flags (`is_loading`, `is_error`, `is_ready`, `has_data`, `is_retrying`) to represent mutually exclusive lifecycle phases. Collapse them into a single discrete enum or tagged union (`State = 'idle' | 'loading' | 'success' | 'error'`).
2. **Make Illegal States Unrepresentable**: Constrain schemas and type models so invalid combinations (e.g. `data != null` combined with `error != null`, or `status == "closed"` with an active trade ID) cannot be expressed in code or stored in the database.
3. **Explicit Transition Matrices**: State mutations must flow through defined transition guards. If an event occurs in an invalid state, it must fail fast with a clear invariant error rather than silently corrupting state.
4. **Derive Rather Than Cache**: Never store duplicate mutable state across components or objects. Derive transient properties from the canonical source of truth on demand.

---

## 2. Canonical State Machine Registry

### 2.1 Trade Validation & Skeptical Verifier Pipeline

- **Source Files**: [`apps/engine/execution/validation.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/execution/validation.py), [`apps/engine/core/models.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/core/models.py), [`apps/engine/pipeline/decision_processor.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/pipeline/decision_processor.py)
- **Type Implementations**:
  - `ValidationStatus(Enum)` in `apps/engine/execution/validation.py`: `PASSED`, `REJECTED_HALLUCINATION`, `REJECTED_LIQUIDITY`, `REJECTED_REDUNDANCY`, `REJECTED_MARKET_CLOSED`, `REJECTED_STALE_QUOTE`, `ERROR_PROVIDER`
  - Downstream pipeline validation in `apps/engine/pipeline/decision_processor.py`: `REJECTED_MARGIN` (insufficient cash/buying power)
  - `VerificationResult.status: Literal["APPROVED", "REJECTED_VERIFICATION", "ADJUSTED_ALLOCATION"]` in `apps/engine/core/models.py`

```text
                        [Proposed Trade Signal]
                                   │
                                   ▼
                       [Deterministic Pre-Validation]
                                   │
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
        [ValidationStatus: PASSED]         [ValidationStatus: REJECTED_*]
                 │                         (HALLUCINATION | LIQUIDITY |
                 │                          REDUNDANCY | MARKET_CLOSED |
                 │                          STALE_QUOTE | ERROR_PROVIDER)
                 ▼                                   │
        [Pipeline Margin Check]                      ▼
                 │                            [Order Blocked]
        ┌────────┴──────────────────────────┐
        ▼                                   ▼
   [Margin OK]                    [REJECTED_MARGIN]
        │                                   │
        ▼                                   ▼
[Skeptical Verifier Agent]            [Order Blocked]
        │
   ┌────┴──────────────────────────────┐
   ▼                                   ▼
[Verification: APPROVED]       [Verification: REJECTED_VERIFICATION]
   │                                   │
   ▼                                   ▼
[Order Dispatched to Alpaca]     [Order Aborted & Logged]
```

- **Invariants**:
  - A trade can only reach Alpaca order generation if `validation_status == ValidationStatus.PASSED`, margin checks succeed, AND `verification_status == "APPROVED"` (or the model is explicitly listed in `SKIP_VERIFIER_OWNER_IDS` per `[[concepts/verifier-bypass]]`).
  - Allocation adjustments (`ADJUSTED_ALLOCATION`) must be clamped to `min_buy_threshold` before execution.

---

### 2.2 Alpaca Broker Order Lifecycle

- **Source Files**: [`apps/engine/scripts/sync_alpaca_orders.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/scripts/sync_alpaca_orders.py), [`apps/engine/execution/alpaca_broker.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/execution/alpaca_broker.py), [`apps/engine/execution/portfolio.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/execution/portfolio.py)
- **Database Column**: `trades.alpaca_status`
- **States**: `SUBMITTED`, `FILLED`, `CANCELED`, `EXPIRED`, `REJECTED`, `ERROR`, `BACKFILLED`, `SKIPPED_NO_POSITION`

```text
                 ┌───────────────────[SUBMITTED]───────────────────┐
                 │          │               │                      │
                 ▼          ▼               ▼                      ▼
             [FILLED]   [CANCELED]      [EXPIRED]              [REJECTED]
                 ▲
                 │ (Reconstructed post-market)
           [BACKFILLED]

 [Submission Exception] ────▶ [ERROR]
 [Exit with zero pos]   ────▶ [SKIPPED_NO_POSITION]
```

- **Invariants**:
  - `SUBMITTED` is the initial state when an order is acknowledged by Alpaca API.
  - Terminal states (`FILLED`, `CANCELED`, `EXPIRED`, `REJECTED`, `ERROR`, `SKIPPED_NO_POSITION`) are immutable in application logic. Once reached, an order record cannot transition back to `SUBMITTED`.
  - `BACKFILLED` is reserved exclusively for post-market reconstructed fills (`[[concepts/backfilled-trades]]`).

---

### 2.3 Daily SPY & TLT Intraday Prediction & Trading Lifecycle

- **Source Files**: [`apps/engine/tasks/daily_predictor.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tasks/daily_predictor.py), [`apps/engine/tasks/bond_predictor.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tasks/bond_predictor.py), [`apps/engine/analysis/daily_postmortem.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/analysis/daily_postmortem.py)
- **Nature**: Multi-phase temporal state machine tied to market hours (`America/New_York`).

```text
  09:15 ET                   09:30 ET                     15:50 ET / Intraday Hit       16:15 ET
[PRE-MARKET PREDICTED] ────▶ [MARKET OPEN ENTERED] ────▶ [POSITION LIQUIDATED] ────▶ [POSTMORTEM AUDITED]
 (prediction stored,         (MOO fill recorded,         (target hit exit OR         (GPT-6 audit runs,
  no trade ID yet)            entry_trade_id bound)       3:50 PM close exit)         root cause classified)
```

- **Invariants**:
  - `entry_trade_id` is assigned strictly at 9:30 AM market open upon fill reconciliation (`[[concepts/session-open-reconciliation]]`).
  - `exit_trade_id` is set strictly once, either by the intraday target limit trigger or the 3:50 PM MOC liquidator.
  - Prediction evaluation (`actual_change_pct`, `direction_hit`) requires the official 4:00 PM close bar; never evaluate using midday quotes.

---

### 2.4 Catalyst Radar 4-Stage Digestion

- **Source File**: [`apps/engine/analysis/catalyst_radar.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/analysis/catalyst_radar.py) (function `calculate_date_offset`)
- **Concept Page**: `[[concepts/catalyst-radar]]`
- **States**: `upcoming` $\to$ `active` $\to$ `digesting` $\to$ `expired`

```text
  [upcoming] ───────────────▶ [active] ───────────────▶ [digesting] ───────────────▶ [expired]
(delta_days > 0,              (delta_days == 0,         (-3 <= delta_days < 0,        (delta_days < -3,
 catalyst in future)           event today)              event occurred 1-3d ago)      catalyst historical)
```

- **Invariants**:
  - Monotonic chronological progression: calculated deterministically from the target event date relative to current evaluation date.
  - Vector similarity clustering occurs during `upcoming` and `active` to link incoming events to persistent macroeconomic narratives.

---

### 2.5 Free LLM Proxy Provider Cooldowns & Live Intraday Streaming

- **Source Files**: [`apps/free_llm_proxy/circuit_breaker.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/free_llm_proxy/circuit_breaker.py), [`apps/free_llm_proxy/server.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/free_llm_proxy/server.py), [`apps/free_llm_proxy/router.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/free_llm_proxy/router.py), [`apps/engine/trading/runner.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/trading/runner.py), [`apps/engine/trading/tape_stream.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/trading/tape_stream.py)
- **Current Runtime Nature**:
  - `CircuitBreaker` in `apps/free_llm_proxy/circuit_breaker.py` tracks provider cooldown timestamps via `_cooldowns: dict[str, float]` and consecutive failure counts via `_failures: dict[str, int]`.
  - A provider is deemed healthy when `now >= cooldown_until`. On HTTP 429 or 2 consecutive 5xx errors, cooldown is set to `now + default_cooldown_seconds` (or parsed `retry-after`).
  - **Deterministic 4xx cooldown**: `_DETERMINISTIC_4XX = frozenset({400, 403, 408, 409, 413, 422})`. These client errors are not transient — they mean the provider cannot serve *this* request at any shape (e.g. Groq's 413 payload-too-large, or a 400 malformed request). They trip an immediate cooldown exactly like a 429, so the provider is skipped on the next attempt instead of being re-probed head-on on every request.
  - **Prompt-size pre-dispatch exclusion**: providers declare an optional `max_prompt_tokens` (Groq: `8000`) in `providers.json`. `Router.get_candidate_chain(requested_model, prompt_tokens=...)` estimates the request size with `estimate_prompt_tokens` (~4 chars/token over message `content` strings and text parts) and drops any provider whose documented ceiling is below the estimate before a round trip is ever attempted. A guaranteed 413 therefore never reaches the network.
  - Routing is cost-segmented: paid providers (`billing: "paid"`) are never placed ahead of a cooling free candidate for the `auto-go` / `auto-strata-go` aliases. Paid eligibility is fail-closed through an `auto_aliases` allowlist, and a paid provider is skipped entirely when its live model catalog is unavailable.
  - The breaker is per provider, not per cost class: `opencode-go` participates in the same cooldown FSM as free providers, but its healthy state never pre-empts the free cooling segment.

```text
       [Provider Healthy: now >= cooldown_until]
                           │
   (HTTP 429 | 2 consecutive 5xx | deterministic 4xx:
    400, 403, 408, 409, 413, 422)
                           ▼
     [Tripped Cooldown: now < cooldown_until]
                           │
             (cooldown seconds elapse)
                           ▼
                  [Provider Healthy]
```

---

### 2.6 Frontend Query Settlement Gate

- **Source File**: [`apps/web/src/lib/query-client.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/lib/query-client.tsx)
- **Concept**: `isQuerySettled(queries, isTransitionPending)`
- **Problem Solved**: Prevents UI flicker, layout shift, and volatile badge popping by collapsing multi-boolean TanStack Query and React states into a binary gate.

```text
┌────────────────────────────────────────────────────────┐
│ Input States:                                          │
│ - query.isPending                                      │
│ - query.isFetching                                     │
│ - query.isPlaceholderData                              │
│ - isTransitionPending (useTransition)                  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
              [isQuerySettled() Evaluation]
                            │
           ┌────────────────┴────────────────┐
           ▼                                 ▼
       [SETTLED]                        [UNSETTLED]
   (Render secondary actions,       (Render stable container,
    interactive badges, D3 charts)   lock secondary telemetry)
```

### 2.7 Daily Stock Picker Arena (`daily_stock_baskets` & `daily_stock_picks`)

- **Source Files**: [`apps/engine/tasks/stock_picker.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tasks/stock_picker.py), [`apps/engine/tasks/evaluate_stock_picks.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tasks/evaluate_stock_picks.py), [`supabase/migrations/20261112000000_create_daily_stock_picks.sql`](file:///home/cv/Documents/Code/llm-market-bench/supabase/migrations/20261112000000_create_daily_stock_picks.sql)
- **States**: `pending` $\to$ `evaluated` | `cancelled`

```text
  09:17 ET (stock-picker)              16:05+ ET (evaluate-stock-picks)
         [pending] ──────────────┬──────────────▶ [evaluated] (valid RTH open > 0 & close)
                                 └──────────────▶ [cancelled] (halt / missing / sub-cent open)
```

- **Invariants**:
  - `chk_pick_evaluation_invariants` enforces that `pending` picks keep `evaluated_at`, `is_hit`, and `close_price` null; `evaluated` picks require `open_price > 0` (checked after 2-decimal rounding) and non-null `close_price`, `stock_return_pct`, `position_return_pct`, `is_hit`, and `evaluated_at`; `cancelled` picks require `is_hit IS NULL`.
  - `session_skip_reason` in `apps/engine/tasks/stock_picker.py` refuses morning overwrites once any basket for `target_date` is `evaluated`, even with `--force`.
  - Evaluation batch upserts merge `{**orig, ...updates}` with `on_conflict="id"` so PostgreSQL `NOT NULL` checks during `INSERT ... ON CONFLICT DO UPDATE` never reject partial payloads, and `cancelled` baskets explicitly clear all six performance metrics.

### 2.8 Dynamic Chunk Error Recovery (`ChunkRecoveryPhase`)

- **Source Files**: [`apps/web/src/utils/chunk-reload.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/utils/chunk-reload.ts), [`apps/web/src/components/ui/DefaultCatchBoundary.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/components/ui/DefaultCatchBoundary.tsx)
- **States**: `checking` (pre-commit render) $\to$ `reloading` $\to$ `dispatched` | `circuit_open`
- **Invariants**:
  - `claimChunkReloadAttempt()` atomically validates `sessionStorage` retry state (`Number.isFinite` and non-negative) and fails closed (`circuit_open`) whenever storage is unavailable, throws `SecurityError`/`QuotaExceededError`, or holds corrupted `NaN` values, preventing infinite reload loops.
  - `DefaultCatchBoundary` claims the slot once per error identity, defers telemetry + dispatch by one macrotask so parent `PostHogProvider` `init()` completes on cold root-level errors, reports `auto_reloaded` truthfully to PostHog (`captureException`), transitions to `dispatched` inside the timer callback before calling `reloadAtTarget()`, and enforces same-origin `#hash`-safe reloading.

### 2.9 Investing Style Diagnostic Session (`QuizSession`)

- **Source Files**: [`apps/web/src/features/personality/PersonalityQuizPage.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/personality/PersonalityQuizPage.tsx), [`apps/web/src/routes/personality.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/routes/personality.tsx)
- **Entity Page**: [[entities/personality-quiz]]
- **States**: `answering` (`stepIndex`, `answers`) | `result` (`mode: 'quiz_match'`, `quizAnswers`) | `result` (`mode: 'inspect'`, `archetypeId`, `quizAnswers`)
- **Invariants**:
  - Illegal `{ phase: 'result', quizAnswers: null, inspectedArchetypeId: null }` states are unrepresentable; `mode: 'quiz_match'` always holds non-null `quizAnswers` and `mode: 'inspect'` always holds a concrete `archetypeId`.
  - Selecting your own matched archetype in `archetype-switcher` transitions back to `mode: 'quiz_match'` rather than showing `buildSharedArchetypeResult`'s reference `98%` fit.
  - `/personality` route passes `onArchetypeSearchChange` using TanStack Router `navigate({ replace: true })`; self-emitted search updates tracked via FIFO `pendingSelfSearchesRef` keep `quizAnswers` intact even across pipelined transitions, while external `?archetype=` transitions or bare `/personality` navigations cleanly re-seed `session`.
  - Async clipboard copy updates `copiedArchetype` inside a `useEffect`-maintained `activeResultArchetypeRef` guard without render-phase ref mutation.

### 2.10 Cedar Sanctuary Backdrop (`MotionState` & `EntranceState`)

- **Source Files**: [`apps/web/src/features/home/backdrop/GardenBackdrop.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/home/backdrop/GardenBackdrop.tsx), [`apps/web/src/features/home/backdrop/garden-scene.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/home/backdrop/garden-scene.ts)
- **Entity Page**: [[concepts/living-scene-backdrops]]
- **States**:
  - `MotionState = 'running' | 'idle' | 'paused'` (eliminates illegal simultaneous `{ running: true, reduced: true }` flags)
  - `EntranceState = { kind: 'animating'; elapsed: number } | { kind: 'settled' }`
- **Invariants**:
  - System `prefers-reduced-motion: reduce` and explicit pause transitions (`settleAndPause`) atomically cancel timeouts/`rAF` and advance `entrance` to `{ kind: 'settled' }`, preventing partially clipped mid-entrance frames.
  - A `0x0` deferred mount does not advance `EntranceState` offscreen; animation begins once `buildLayers()` initializes a non-empty `Scene`.
  - `buildLayers()` checks `(width, height, dpr, atmosphere, backingWidth, backingHeight)` before allocating or clearing offscreen canvases.

### 2.11 `/build` Bot Builder Conversation (`BuilderPhase`) & Run Status Poll

- **Source Files**: [`apps/web/src/features/recipes/builder/builder-phases.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/recipes/builder/builder-phases.ts), [`apps/web/src/features/recipes/builder/use-builder-chat.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/recipes/builder/use-builder-chat.ts), [`apps/web/src/features/recipes/utils/use-latest-recipe-run.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/recipes/utils/use-latest-recipe-run.ts)
- **Entity Page**: [[concepts/recipe-builder-compiler]]
- **States**:
  - `BuilderPhase = 'idle' | 'signed-out' | 'compiling' | 'question' | 'declined' | 'ready' | 'error'` — one derived value from `(error, isCompiling, reply, userId)`, rendered by `BuilderStatusStrip`; no boolean fan-out for "loading"/"failed".
  - Compile transport: `idle` $\\to$ `compiling` $\\to$ `question` (waits for the user) $\\to$ `compiling` … $\\to$ `ready` | `declined` | `error`.
  - Backtest run poll: `no run` $\\to$ `pending` $\\to$ `processing` $\\to$ `completed` | `failed` | `cancelled`; only `pending`/`processing` is polled (`refetchInterval`), so a settled run costs one read.
- **Invariants**:
  - A reply is accepted only when `isCompilerReply()` validates it (an `ok` strategy must pass `validateStrategy`); the transport resolves an envelope-less response to `undefined`, so the boundary asserts with `assertServerFnResult()` instead of dereferencing it.
  - `error` and `reply` are never both set: a failed compile clears the reply, so question buttons cannot stay clickable beside a failure message.
  - `inFlight` is a ref latch, not state — two clicks in one tick must not spend two metered compiles.
  - The compile has one budget (`BUILDER_BUDGET_MS`, 24s) under the measured ~28–30s origin ceiling; a timeout degrades straight to a starter template instead of retrying inside a 3s window.
  - The strip's elapsed clock is `aria-hidden` and outside the polite live region, so a countdown does not queue one screen-reader announcement per second.

---

## 3. Implicit State Debt & Refactoring Backlog

The following areas in the codebase currently manage state implicitly through combinations of nullable columns, flags, or string literals, and are targeted for systematic collapse into explicit types and constraints:

| Surface | Current Implicit Mechanism | Target Refactored State |
| :--- | :--- | :--- |
| **Daily Predictions Lifecycle** | Split-brain: PostgreSQL check constraint permits only `('pending', 'evaluated')` while intermediate phases (`ENTERED`, `TARGET_EXITED`, `CLOSE_EXITED`) are inferred from nullable FKs (`entry_trade_id`, `exit_trade_id`). | Formal migration adding an explicit enum/check constraint: `DailyPredictionStatus = 'PREDICTED' \| 'ENTERED' \| 'TARGET_EXITED' \| 'CLOSE_EXITED' \| 'EVALUATED'` |
| **Alpaca Trades Status** | `trades.alpaca_status` is an unconstrained `TEXT DEFAULT NULL` column without database-level enum or transition check constraints. | Add PostgreSQL enum type or `CHECK (alpaca_status IN ('SUBMITTED', 'FILLED', 'CANCELED', 'EXPIRED', 'REJECTED', 'ERROR', 'BACKFILLED', 'SKIPPED_NO_POSITION'))` with a transition trigger preventing backward moves. |
| **LLM Proxy Circuit Breaker** | Cooldown timestamps allow thundering herds when a 60-second window expires; all concurrent requests hit the provider simultaneously. | Formal FSM: `CLOSED` $\to$ `OPEN` $\to$ `HALF_OPEN` with single-canary mutex probe gating before full traffic resumption. |
| **Autoresearch Experiments** | `evaluated_at IS NULL`, `is_champion` boolean, `score IS NULL`. | `ExperimentState = 'PENDING_EVALUATION' \| 'EVALUATED' \| 'CHAMPION' \| 'PRUNED'` |
| **Systematic Sector Horizons** | `exit_date IS NULL` combined with application date math. | `PositionHorizonState = 'OPEN' \| 'MATURED_HOLD' \| 'EXIT_QUEUED' \| 'CLOSED'` |
| **Live Trader WebSocket Session** | Ambient client connections and disconnected flags. | `StreamSessionState = 'CONNECTING' \| 'STREAMING' \| 'RECONNECTING' \| 'DISCONNECTED'` |

### 3.1 Strategy Builder Studio, Incremental Backtest & Preview (`ExecutionState`, `RecipeJobStatus`, `PreviewState`, `RecipeSaveState`)

- **Source Files**:
  - [`apps/web/src/features/recipes/types.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/recipes/types.ts) ([`RecipeStudioPage.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/recipes/pages/RecipeStudioPage.tsx), [`RecipeBacktestPage.tsx`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/recipes/pages/RecipeBacktestPage.tsx))
  - [`apps/web/src/features/recipes/utils/use-recipe-draft.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/recipes/utils/use-recipe-draft.ts) (`RecipeSaveState`, `RecipeSaveError`)
  - [`apps/engine/recipes/worker.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/recipes/worker.py) ([`push_runner.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/recipes/push_runner.py))
- **States**:
  - `ExecutionState` (inline in Studio): `idle` $\to$ `running` (`live_turn` | `backtest`) $\to$ `live_done` | `error` (`kind: 'navigation'` requiring `backtestJobId`, `kind: 'quota'` optionally preserving `backtestJobId`, or `kind: 'execution'` with no `backtestJobId`). Enforces a mutual-exclusion `isBusy` lock across execution, live-schedule toggles, draft saves, and template switches; when `mode === 'backtest'`, enqueueing navigates to `/recipes/backtest/$jobId` (falling back to the top alert link if navigation rejects).
  - `RecipeSaveState` (`useRecipeDraft`): `idle` $\to$ `saving` $\to$ `saved` | `error`, with any edit returning it to `idle`. Guarded by two monotonic counters: `draftRev` (a response landing against a newer revision adopts the saved row `id` but never overwrites the local draft, and settles to `idle` rather than `saved`) and `generation` (a response from a draft that was replaced by a template is ignored entirely, so it cannot stamp the old row id onto a fresh template). `isSaving` is cleared only when the request settles — never by an edit — so `isBusy` stays true for the whole flight. A save requested at an advanced revision chains a second persist after the in-flight one, so a queued run always enqueues the edited graph. Failures rethrow as `RecipeSaveError`, which routes the message to the inline name-field alert instead of the top `StudioAlertSlot`.
  - `RecipeJobStatus` (`recipe_execution_queue`): `pending` $\to$ `processing` (dual-lane dequeue via `pop_next_recipe_job(target_mode)`, streaming per-slot `progress_pct`, `heartbeat_at`, and `result_json.day_steps` from `BacktestAccumulator`) $\to$ `completed` | `failed` | `cancelled`.
  - `PreviewState`: `template` $\to$ `loading` $\to$ `hydrated` | `error`
- **Cardinality invariant**: `PushStrategy.stages` is the one-element tuple `[StrategyStage]`, so the zero-stage and multi-stage states are unrepresentable in the type. The engine schema (`apps/engine/recipes/push_schema.py`) and the `strategy_recipes_single_stage_check` constraint enforce the same rule at runtime. `StrategyStage` carries only `id`, `blocks`, and `selected_tools` — the obsolete per-stage `title` was removed from the web type, the engine schema, the starter template, and stored `graph_json` (migration `20261116010000_strip_recipe_stage_title.sql`). See [[entities/recipe-studio]].

---

## 4. Verification & Audit Mandate

Whenever modifying any state machine or lifecycle:
1. Verify the change against this registry.
2. Ensure illegal states cannot be created or queried.
3. Update this page as part of **Tier 8 (Wiki Synchronization)** in [`.agents/skills/verify/SKILL.md`](file:///home/cv/Documents/Code/llm-market-bench/.agents/skills/verify/SKILL.md).
