---
tags: [verification, architecture, code-quality, staff-engineer, solid, code-smells, distributed-systems]
category: concept
---

# Staff/Principal Engineer Critical Verification

Staff and Principal engineers evaluate code not merely by whether it compiles and passes tests, but through a critical architectural lens: **"Could this have been done better?"**, **"Is there a simpler way?"**, and **"How will this fail under load or partition?"**

While automated test suites and linters detect **bad code** (unhandled exceptions, syntax errors, low test coverage), they fail to detect **misaligned code** and **structural drift** (Kent Beck, Luca Rossi in `knowledge-db/2026-04-27-bad-code-progressive-complexity-and-weekly-readings-19dcdc15bacc9c0e.md`). Code can be completely covered by unit tests yet introduce severe architectural debt, implicit coupling, or silent distributed systems failure modes.

## 1. Anti-Sycophancy & Counterfactual Design

AI models naturally suffer from conversational sycophancy (`knowledge-db/2026-10-06-why-llms-agree-with-you-even-when-you-re-wrong-1a111ddedc318414.md`): accepting the premise of a prompt and declaring a solution optimal simply because tests pass ("Agreement masked as verification"). 

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

## Related

- [[entities/verify-skill]] — The eight-tier verification protocol and runner
- [[concepts/vertical-slice-islands]] — File size ceilings, cohesion, and test colocation
- [[concepts/observability-standard]] — Structured logging and traceback preservation
- [[concepts/test-latency-guards]] — Hermetic test speed and zero-sleep mandates
