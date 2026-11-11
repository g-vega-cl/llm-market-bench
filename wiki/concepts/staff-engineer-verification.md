---
tags: [verification, architecture, code-quality, staff-engineer, solid, code-smells, distributed-systems, state-machines, debugging]
category: concept
---

# Staff/Principal Engineer Critical Verification

Staff and Principal engineers evaluate code not merely by whether it compiles and passes tests, but through a critical architectural lens: **"Could this have been done better?"**, **"Is there a simpler way?"**, and **"How will this fail under load or partition?"**

While automated test suites and linters detect **bad code** (unhandled exceptions, syntax errors, low test coverage), they fail to detect **misaligned code** and **structural drift** (Kent Beck, Luca Rossi in `knowledge-db/2026-04-27-bad-code-progressive-complexity-and-weekly-readings-19dcdc15bacc9c0e.md`). Code can be completely covered by unit tests yet introduce severe architectural debt, implicit coupling, or silent distributed systems failure modes.

## 1. Anti-Sycophancy & Counterfactual Design

AI models naturally suffer from conversational sycophancy (`knowledge-db/2026-10-06-why-llms-agree-with-you-even-when-you-re-wrong-1a111ddedc318414.md`): accepting the premise of a prompt and declaring a solution optimal simply because tests pass ("Agreement masked as verification"). 

### 1.1 The Isolated Subagent Red-Team Pattern

When the agent that writes code also performs the staff review in the same conversation turn, cognitive dissonance and self-justification degrade the review into rubber-stamping. To break this feedback loop:
- **Cold Review Boundary**: The main agent spawns an isolated `research` subagent passing *only* the git diff and objective requirements. The main agent is prohibited from priming or defending the implementation.
- **Adversarial Mandate**: The subagent explicitly hunts for leaky abstractions, race conditions, edge-case failures, and architectural drift.
- **Triage Loop**: Tactical bugs caught by the subagent are fixed immediately; structural critiques are recorded as debt rather than being rationalized away.

Staff-level review forces counterfactual examination before committing any change:

1. **The "Do Nothing / Delete" Check**:
   - Could this requirement be satisfied by removing code, leveraging an existing PostgREST query, or reusing an existing utility instead of adding new lines?
2. **The Second Design Comparison**:
   - Formulate at least one viable alternative design (e.g. batch database query vs in-memory transformation, pure functional mapping vs stateful class, CSS Grid vs JavaScript layout).
   - Articulate the concrete tradeoff (latency, memory footprint, coupling, maintainability) that justifies the chosen design.
3. **Make the Hard Change Easy (Tidy First)**:
   - Avoid tacking special cases and boolean parameters onto already complex functions. If an existing routine resists clean extension, refactor the structure first, then make the change.

## 2. SOLID Principles in Practice

- **Single Responsibility Principle (SRP) & Functional Core / Imperative Shell**:
  - Keep domain calculations, math models, and business decisions pure and isolated from I/O, database queries, and external network clients.
  - If a function queries Supabase, calculates Sharpe ratios, and updates a state cache, decompose it into a pure calculator function wrapped by an orchestration shell.
- **Open/Closed Principle (OCP) via Data-Driven Dispatch**:
  - Replace sprawling `if/elif/else` chains with dictionary dispatch maps, typed registries, or schema configurations (e.g. `packages/config/tools.json` and CLI subcommand routers).
- **Liskov Substitution Principle (LSP)**:
  - Subclasses or mock implementations must satisfy all behavioral contracts, preconditions, and postconditions of the parent interface without raising surprise errors.
- **Interface Segregation Principle (ISP)**:
  - Keep interfaces and function signatures narrow. Accept only the specific fields or typed attributes needed rather than passing god-objects, entire database rows, or oversized context dictionaries.
- **Dependency Inversion Principle (DIP)**:
  - Depend on abstractions or pass dependencies explicitly (such as via client fixtures or `resolve_dep` seams) to avoid deep monkeypatching and brittle coupling.

## 3. Code Smells & Complexity Ceilings

Review diffs for recurring code smells:

- **Shotgun Surgery**: A single conceptual change requiring edits across many disjoint modules indicates missing abstraction or leaky encapsulation.
- **Primitive Obsession & Data Clumps**: Passing identical groups of raw primitives (`ticker`, `start_date`, `end_date`, `price`) across multiple functions instead of bundling them into a `dataclass`, `TypedDict`, or Pydantic model.
- **Feature Envy & Law of Demeter**: A function accessing and manipulating another object's internal fields more than its own. Avoid chaining deep access (`a.b.c.get("d")`).
- **Boolean Blindness & Deep Nesting**: Flags like `process_data(data, True, False, True)` obscure behavior. Use explicit enums, keyword arguments, or separate functions. Keep nesting depth under 4 levels using early guard clauses.
- **Hidden Side Effects**: Functions named `get_*` or `compute_*` that silently mutate input lists, write to disk, or update global variables.
- **McCabe Cyclomatic Complexity (`C901`)**:
  - Target $\le 10$ decision points per function; hard ceiling at $15$.
  - Functions exceeding 15 branches must be decomposed into pure helper sub-routines or data-driven tables.

## 4. Distributed Systems & Failure Modes (CAP / PACELC)

Systems running background cron jobs, database persistence, and external APIs operate as distributed systems:

- **Explicit CAP Stance**:
  - **CP (Consistency / Partition Tolerance)**: Critical financial paths (trade execution, Reg T margin enforcement, portfolio balance updates) must fail closed rather than execute on stale, uncertain, or corrupt state.
  - **AP / EL (Availability / Eventual Consistency)**: Presentation and exploratory paths (dashboard charts, non-critical news feeds, speculative AI commentary) should degrade gracefully using cached state or sensible defaults.
- **Trade and Pipeline Idempotency**:
  - Workflows must survive mid-execution crashes. Ensure database writes use unique constraint upserts (`ON CONFLICT DO UPDATE`) and deduplication keys so re-running a failed job does not double-count trades or records.
- **Bulkheads & Timeout Isolation**:
  - Every external network or database operation must specify explicit timeouts. Use concurrency limits (`asyncio.Semaphore`) to avoid saturating database connection pools.

## 5. Performance & Resource Intuition (Orders of Magnitude)

Staff engineers think in physical orders of magnitude:
- CPU Cache: ~1 nanosecond
- RAM Access: ~100 nanoseconds
- NVMe SSD / Disk I/O: ~10–100 microseconds
- Cross-Data-Center Network / Database Query: ~10–100 milliseconds

**Key Rules**:
- **Zero N+1 Query Loops**: Never execute database queries, HTTP calls, or file reads inside loops over records. Batch into `.in_()` queries or bulk inserts.
- **Algorithmic Complexity**: Prefer $O(1)$ set/dictionary lookups over $O(N)$ repeated list scans.
- **Memory & Egress Hygiene**: Strip unused heavy columns (e.g. pgvector `embedding` arrays) from read queries via explicit column projections (`[[concepts/vector-egress-stripping]]`).

## 6. The 5-Step System Design Interview Framework

When auditing features, treat the pull request as an L5/L6 System Design Interview (based on the framework by Neo Kim & Abdirahman Jama in `knowledge-db/2026-03-07-i-struggled-with-system-design-interview-until-i-learned-thi-19cc890c76fbffe2.md`):

1. **Functional & Non-Functional Boundaries**:
   - What are the core user flows? What is explicitly out of scope?
   - What are the execution frequency and latency constraints (sub-100ms UI response vs background cron batch)?
2. **Core Data, Mutability & Index Alignment**:
   - *Append-only vs mutable*: What can never be lost? Financial state (trades, account mutations) must be strictly append-only with compensating cancellation/reversal records. Never use destructive `DELETE` operations that wipe out audit trails.
   - *Index alignment*: Every `.eq()`, `.gte()`, or `.order()` query must be backed by a composite index in `supabase/migrations/` to prevent sequential table scans as tables grow.
   - *Unbounded scan prevention*: Queries on growing historical tables must enforce explicit date windows (`gte`/`lte`), pagination, or `.limit()`.
3. **End-to-End Data Flow & Caching**:
   - Trace the write-to-read lifecycle: Background pipeline write -> PostgREST -> TanStack Query cache / query keys -> UI presentation.
   - Verify cache invalidation, staleness bounds (`staleTime`/TTL), and prevent partial-write visibility to concurrent readers.
4. **Bottlenecks, Single Points of Failure (SPOFs) & Graceful Degradation**:
   - Identify SPOFs: What happens if an external dependency (local Strata/Laya server, FMP, OpenRouter, Alpaca, Supabase) is down, times out, or returns a 429/500? Ensure pipelines fail fast or degrade gracefully with fallback without corrupting state.
   - Bulkheads & timeouts: Explicit timeouts on all network calls and concurrency limits (`asyncio.Semaphore`).
5. **Tradeoffs & 10x Scale Limits**:
   - What compromises were made for simplicity, what architectural debt was incurred, and what will break first under 10x volume, extreme volatility regimes, or concurrent execution?

## 7. State-Space Minimization ("Make Illegal States Unrepresentable")

Systems with unbounded or loosely typed state suffer from combinatorial explosion ($2^N$ states for $N$ boolean flags) and implicit edge states that escape unit test coverage. During Staff/Principal review, verify state design against `[[concepts/state-machines]]`:

1. **Eliminate Boolean Flag Sprawl**:
   - Prohibit compound boolean flags (`is_loading`, `is_error`, `is_ready`, `has_data`, `is_retrying`) to represent mutually exclusive lifecycle phases.
   - Collapse them into a single discrete enum (`StrEnum`) or TypeScript discriminated union / Python literal union (`State = 'idle' | 'loading' | 'success' | 'error'`).
2. **Make Illegal States Unrepresentable**:
   - Design types and schemas such that invalid combinations (e.g. `data != null` combined with `error != null`, or `status == "closed"` holding an active order ID) cannot be expressed or queried.
3. **Explicit Transition Matrices & Guards**:
   - Every state mutation must flow through defined transition guards. If an unexpected event occurs, fail fast immediately with an invariant error rather than silently corrupting state.
4. **Derive Rather Than Cache**:
   - Never store duplicate mutable state across components or objects. Derive transient properties from the canonical source of truth on demand.
5. **Implicit State Debt Triage**:
   - Check if the modified code relies on multi-column nullable combinations (e.g., `evaluated_at IS NULL AND exit_trade_id IS NOT NULL`) and systematically refactor toward explicit lifecycle status types.

## 8. The 10/10 Agentic Debugging Protocol

When tests or verification checks fail during implementation, AI agents frequently fall into **"Shotgun Debugging"**—blindly editing files, tacking on boolean flags, or patching symptoms until tests pass. Staff-level verification enforces a strict 5-step investigative loop:

1. **Locate & Reproduce**:
   - Pinpoint the exact origin. Write or isolate a minimal, hermetic reproduction test case first (TDD).
2. **Formulate Hypotheses**:
   - List 2 to 3 distinct potential root causes before touching production code. Rank them by architectural probability.
3. **Gather Evidence**:
   - Trace data flow across boundaries (validation -> computation -> persistence -> presentation). Inspect variable states and error tracebacks via scratch scripts.
4. **State-Space & Root Cause Isolation**:
   - Identify the exact invalid state, illegal transition, or broken invariant causing the defect. Explain *why* the failure happens, not just *what* failed.
5. **Minimal Fix & Proof**:
   - Apply the minimal necessary architectural fix. Eliminate the invalid state permanently and prove all hermetic tests pass with zero regressions.

## Related

- [[concepts/state-machines]] — Canonical registry of explicit and implicit finite state machines
- [[entities/verify-skill]] — The eight-tier verification protocol and runner
- [[concepts/vertical-slice-islands]] — File size ceilings, cohesion, and test colocation
- [[concepts/observability-standard]] — Structured logging and traceback preservation
- [[concepts/test-latency-guards]] — Hermetic test speed and zero-sleep mandates
