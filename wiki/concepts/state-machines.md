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
 (prediction stored,         (MOO fill recorded,         (target hit exit OR         (GPT-5.6 audit runs,
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

### 2.6 Strategy Builder MVP Execution & Preview (`ExecutionState` / `PreviewState`)

- **Source File**: [`apps/web/src/features/recipes/types.ts`](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/features/recipes/types.ts) (`RecipeStudioPage.tsx`)
- **States**:
  - `ExecutionState`: `idle` $\to$ `running` (`live_turn` | `backtest`) $\to$ `live_done` | `backtest_done` | `error`
  - `PreviewState`: `template` $\to$ `loading` $\to$ `hydrated` | `error`
- **Cardinality invariant**: `PushStrategy.stages` is the one-element tuple `[StrategyStage]`, so the zero-stage and multi-stage states are unrepresentable in the type. The engine schema (`apps/engine/recipes/push_schema.py`) and the `strategy_recipes_single_stage_check` constraint enforce the same rule at runtime. See [[entities/recipe-studio]].

---

## 4. Verification & Audit Mandate

Whenever modifying any state machine or lifecycle:
1. Verify the change against this registry.
2. Ensure illegal states cannot be created or queried.
3. Update this page as part of **Tier 8 (Wiki Synchronization)** in [`.agents/skills/verify/SKILL.md`](file:///home/cv/Documents/Code/llm-market-bench/.agents/skills/verify/SKILL.md).
