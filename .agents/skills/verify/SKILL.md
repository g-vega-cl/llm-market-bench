---
name: verify
description: Run an exhaustive verification protocol after coding to guarantee zero regressions, passing builds, hermetic test isolation, domain financial sanity, and strict architectural compliance.
---

# Code verification protocol

Use this skill after every coding round or when invoking `/verify` to audit changes against production standards before marking work complete.

## 1. Quick execution commands

Run the relevant checks for the modified surfaces:

```bash
# Static hygiene, wiki synchronization & bug hotspot forensics
./apps/engine/.venv/bin/ruff check apps/engine/
./apps/engine/.venv/bin/ruff format --check apps/engine/
pnpm biome check
./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --since "60 days ago" --top 15 --write-wiki
./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py --fix
qmd update && qmd embed

# Web types and build
cd apps/web && pnpm run typecheck
cd apps/web && pnpm run build

# Hermetic test suites with coverage (Parallel vs Sequential)
./apps/engine/.venv/bin/python3 -m pytest -n auto --cov=. --cov-config=.coveragerc # Parallel (fast)
./apps/engine/.venv/bin/python3 -m pytest --cov=. --cov-config=.coveragerc         # Sequential (1 worker, minimal CPU/RAM)
cd apps/web && pnpm test -- --coverage                                            # Web tests (parallel)
cd apps/web && pnpm test -- --maxWorkers=1 --coverage                             # Web tests (sequential)
```

Or run the bundled verification runner:

```bash
./.agents/skills/verify/scripts/verify.sh              # Full suite (parallel, -n auto)
./.agents/skills/verify/scripts/verify.sh --sequential # Full suite (strictly 1 worker, low CPU/RAM)
./.agents/skills/verify/scripts/verify.sh --fast       # Lint, format, types, and wiki (no tests)
./.agents/skills/verify/scripts/verify.sh --hotspots   # Hotspot forensics & coupling
```

---

## 2. Verification tiers

Audit all changed files through these eight tiers. Do not skip any tier.

### Tier 1. Static hygiene, size ceilings, and hotspot forensics

1. **Lint and format**:
   - Python: Ruff rules E, F, I, UP, B, SIM with zero warnings.
   - TypeScript: Biome checks pass with zero errors.
2. **File size ceilings** (Principle 10):
   - Soft ceiling: Under 400 lines of code. Extract sub-modules if exceeding 400 LOC.
   - Hard ceiling: Never exceed 800 lines.
3. **Colocated tests** (Principle 10):
   - Every modified module or component island must have its test sitting immediately next to it (`foo.py` with `test_foo.py`, `foo.tsx` with `foo.test.tsx`).
4. **Code bug hotspots and temporal coupling** (Principle 6):
   - Run `apps/engine/hotspots.py`. Check if any modified file is flagged as `CRITICAL` or `HIGH` risk (e.g., `daily_predictor.py`, `DailyPredictionsPage.tsx`, `market_data.py`, `tools.py`).
   - High fix-ratio files ($>25\%$) require defensive testing and narrow diffs. Avoid bundling speculative refactoring into fixes on these files.
   - Verify strongly coupled companions stay in sync:
     - `daily_predictor.py` $\leftrightarrow$ `test_daily_predictor.py`
     - `DailyPredictionsPage.tsx` $\leftrightarrow$ `DailyPredictionsPage.test.tsx`
     - `core/llm/tools.py` $\leftrightarrow$ `packages/config/tools.json` $\leftrightarrow$ `program.md` $\leftrightarrow$ `test_tools_consistency.py`
     - `researcher.py` $\leftrightarrow$ `handlers/base.py` $\leftrightarrow$ `tools.py`
     - `market_data.py` $\leftrightarrow$ `test_market_data.py`
5. **Engine import root hygiene & CI working directory parity**:
   - Engine production code (`apps/engine/core/`, `apps/engine/tasks/`, `apps/engine/execution/`, `apps/engine/local_autoresearch/`, etc.) must NEVER import with `from apps.engine.` or `import apps.engine.`. All engine code must use imports relative to the `apps/engine` root (e.g. `from core.`, `from tasks.`, `from local_autoresearch.`).
   - In CI/CD runners, tests run with `working-directory: apps/engine`. Any import assuming `apps` is in `sys.path` will fail with `ModuleNotFoundError: No module named 'apps'`.
   - Packages inside `apps/engine` must contain `__init__.py` files so they are treated as standard Python packages.


### Tier 2. Build and type integrity

1. **TypeScript compilation & typecheck enforcement**:
   - `pnpm run typecheck` passes with zero type errors.
   - **Mandatory for web modifications**: Neither `pnpm test` (Vitest) nor `pnpm biome check` executes type checking. They transpile code and run runtime checks, stripping TypeScript types without checking compatibility. You MUST run `cd apps/web && pnpm run typecheck` (or `pnpm run build`) whenever any `.ts` or `.tsx` file is created or modified.
   - No `any` escapes or unsafe type assertions on external API payloads.
2. **Web production build**:
   - `pnpm run build` succeeds without bundle errors or missing environment variable crashes.
3. **Subprocess execution safety**:
   - Python subprocess calls with compound commands (`&&`, `export`, pipes) must invoke bash or use file scripts. Never invoke compound commands directly without a shell wrapper.
   - Never run multiline inline `-c` commands. Use `.scratch/` scripts (Principle 12).
4. **CI workflow secret parity**:
   - If adding or updating environment variables or model providers in `apps/engine/core/config.py`, verify that every invoked GitHub Actions workflow in `.github/workflows/*.yml` explicitly injects them in its step `env:` blocks. Omitting keys causes CI runner failures.

### Tier 3. Hermetic testing and coverage

1. **Zero external network calls** (Principle 3):
   - Unit and integration tests must never connect to live sockets or make external DNS queries.
   - Mock all external interfaces (`httpx`, `requests`, Supabase, FMP, FRED, Alpaca, LLM clients).
2. **Ambient environment isolation**:
   - Tests must pass in a clean environment without relying on ambient environment variables (e.g., `FMP_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`).
3. **Coverage thresholds**:
   - Engine coverage must remain $\ge 70\%$.
   - Web coverage must remain $\ge 40\%$.
4. **TDD reproduction check**:
   - Bug fixes and new features must include a test that would fail without the change and passes with it.
5. **CI working directory test parity**:
   - Tests must pass when executed from `apps/engine` as the working directory (`cd apps/engine && python3 -m pytest -n auto`), matching `.github/workflows/ci.yml`. Never rely solely on running pytest from the repository root, as ambient editable `.pth` files can mask import path mismatches.

### Tier 4. Domain, API, and financial invariants

1. **Financial and schema sanity** (Principle 7):
   - Realistic values: Bounds check implied volatility (non-negative), valid spot prices, valid option chain deltas, and non-zero Put/Call distributions.
   - Spot vs futures separation: Do not mix spot VIX with VIX futures ETFs.
2. **API error handling**:
   - Verify explicit handling for HTTP 401 (auth), 403 (tier forbidden), 429 (rate limits), and 400 (bad parameters).
   - Empty/weekend handling: Verify code handles zero rows or missing trading day data gracefully.
3. **Calendar, timezone, and schedule guards**:
   - Timezone localization: Never use naive `datetime.now()`. All market hours, calendar math, and predictor runs must explicitly use the `America/New_York` timezone.
   - Guard against non-trading days, weekends, holidays, and after-hours execution in daily predictor and trading pipelines.
4. **Trading order safety**:
   - Enforce trade idempotency on re-evaluations.
   - Enforce FIFO lot matching on positions.
   - Prevent accidental short positions when submitting exit SELL orders.
5. **Database migration, RLS, and self-hosted schema parity**:
   - *RLS enforcement*: Any new table created in `supabase/migrations/*.sql` must explicitly include `ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;` and explicit `GRANT` statements per `[[concepts/supabase-grant-convention]]` and `[[concepts/rls-enforcement-standard]]`.
   - *Migration integrity check*: Migrations are version-controlled in `supabase/migrations/` and verified hermetically via `apps/engine/tests/test_migration_grants.py`. Unapplied migrations should be applied to the self-hosted PostgreSQL database (`docker/archive/docker-compose.yml`, `https://benchify-archive-db.clvg.uk`) to maintain schema parity.
   - *Secondary edge replica & PostgREST schema reload (MANDATORY on migrations)*:
     - Physical streaming replication on the MiniPC edge replica (`cv-minipc@minipc`) does NOT forward PostgreSQL `NOTIFY` events (`NOTIFY pgrst, 'reload schema'`), and standby PostgREST runs with `PGRST_DB_CHANNEL_ENABLED: false`.
     - Because `docker/archive/nginx.secondary.conf` routes all `GET` read queries directly to MiniPC PostgREST, leaving the replica un-restarted will cause silent `PGRST205: Could not find table ... in schema cache` failures on public web read paths (`https://benchify-archive-db.clvg.uk`).
     - Whenever migrations are created or applied, you MUST deploy to the MiniPC edge node:
       ```bash
       ./docker/archive/deploy_secondary.sh cv-minipc@minipc
       ```
       (which syncs configs, executes `docker compose restart archive-postgrest` on the replica to force schema cache reload, and probes health).
     - Then execute a live read probe against `SUPABASE_PROJECT_URL` (`https://benchify-archive-db.clvg.uk/rest/v1/<new_or_modified_table>?limit=1`) to confirm `200 OK` and zero `PGRST205` errors.
   - *System portfolio & entity online verification*: When adding or updating system portfolios (`sys-*`) or baseline benchmark models, run a live read-only verification probe against the primary PostgREST database (`SUPABASE_PROJECT_URL`, via diagnostic scratch script) to ensure initial records are provisioned in the `portfolios` table with initial cash balances and Reg T metrics before deployment.
6. **Tool definition parity**:
   - When introducing or altering tools, keep all four locations synchronized:
     1. `packages/config/tools.json`
     2. `apps/engine/core/llm/tools.py`
     3. `apps/engine/autoresearch/program.md`
     4. `apps/engine/tests/test_tools_consistency.py`

### Tier 5. Architecture, UI/UX, and design system

1. **Zero frontend compute** (Principle 9):
   - The web layer is presentation only.
   - Heavy aggregations, math, and multi-table joins must be computed in engine background pipelines and materialized in the database.
2. **Design system compliance** (Principle 11):
   - Strictly consume `@llm-market-bench/ui-design-system` components (`Button`, `Card`, `Badge`, `SectionHeading`, `Table`).
   - Zero arbitrary Tailwind values: Never use square-bracket escapes (`w-[240px]`, `bg-[#1a2b3c]`).
   - Prefer component props (`colorScheme`, `variant`, `size`, `radius`) over custom class overrides.
   - Single dark theme: Never introduce light/dark toggles or conditional `dark:` classes.
3. **Fluent responsive layout** (Principle 13):
   - No explicit media query breakpoints (`sm:`, `md:`, `lg:`).
   - Use CSS Grid `repeat(auto-fit, minmax(...))` and Flexbox `flex-wrap`.
   - Prevent overflow: Apply `min-w-0` on flex items and `whitespace-pre-wrap break-words` on preformatted blocks.
4. **Tool-first LLM architecture** (Principle 8):
   - For autonomous analysis and predictor agents, provide callable tools in `tools.json`. Do not bloat prompts with raw data dumps or hardcode trading heuristics into system prompts.

### Tier 6. Observability and error resilience

1. **Traceback preservation** (Principle 5):
   - In `except` blocks, log with `logger.exception("Context message")` instead of raw string logging or `print()`.
2. **No swallowed errors**:
   - Never write empty `except:` or `except Exception: pass` blocks without logging the traceback.

### Tier 7. Staff/Principal critical code and architecture review

Apply a rigorous staff/principal engineering audit to all changed code. Think counterfactually: **"Could this have been done better?"**, **"Is there a simpler, more robust way?"**, and **"How will this fail?"** See `[[concepts/staff-engineer-verification]]`.

1. **Mandatory Adversarial Subagent Audit**:
   - To eliminate author bias and conversational sycophancy, the main agent MUST invoke an isolated `research` subagent via `invoke_subagent` (`TypeName: "research"`, `Role: "Staff Engineer Reviewer"`).
   - **Cold Context Mandate**: The prompt to the subagent must contain ONLY the 1-sentence task goal and the git diff (`git diff HEAD~1` or staged/working diff). The main agent is **strictly prohibited from providing justifications or rationalizations** to the reviewer.
   - **Adversarial Posture**: The subagent assumes the code contains flaws, anti-patterns, or fragility under load, auditing against `GEMINI.md` mandates, SOLID principles, trade idempotency, and scaling limits.
   - **Triage Protocol**:
     - *Tactical defects* (e.g., swallowed exceptions, missing idempotency guards, prompt leaks, improper imports): Main agent must fix them immediately and re-verify.
     - *Structural pushback* (e.g., shotgun surgery, primitive obsession, missing domain abstraction): Main agent must document the debt transparently as `WARN` or `FAIL` in the report for the user's decision.
2. **Anti-sycophancy and counterfactual critique**:
   - Never accept code just because tests pass.
   - *The delete check*: Could this problem be solved by deleting code, using an existing PostgREST query, or configuring an existing module rather than adding new code?
   - *The second design comparison*: Articulate at least one alternative design and state the concrete tradeoff (latency, memory footprint, coupling, maintainability) justifying the chosen implementation.
   - *Tidy First*: Ensure hard changes were made easy before making the change. Do not tack boolean parameters or special cases onto already complex functions.
3. **SOLID principles & functional core / imperative shell**:
   - *Single Responsibility (SRP)*: Keep math, modeling, and domain decisions pure; separate them from I/O, database queries, and network clients.
   - *Open/Closed (OCP)*: Replace growing `if/elif` ladders with declarative dispatch tables or configuration mappings.
   - *Interface Segregation & Dependency Inversion (ISP/DIP)*: Pass narrow, typed inputs rather than god-objects. Inject external dependencies to keep units hermetically testable.
4. **Code smells and complexity ceilings**:
   - *McCabe Cyclomatic Complexity (`C901`)*: Target $\le 10$ decision branches per function; hard ceiling at $15$. Decompose functions exceeding 15 branches into pure helpers or data-driven tables.
   - *Smell check*: Look for shotgun surgery (touching >10 production files for one change), primitive obsession (raw untyped dicts passed around), feature envy, boolean blindness, deep nesting (>3 levels), and hidden side effects in getters/calculators.
5. **Distributed systems invariants and CAP/PACELC tradeoffs**:
   - *Explicit CAP stance*: Financial ledger mutations and Reg T margin checks must be strictly **CP** (fail closed on partition/staleness). Read paths and non-critical commentary are **AP/EL** (degrade gracefully with cached state).
   - *Idempotency*: Workflows and DB mutations must be safe to re-run mid-flight (`ON CONFLICT DO UPDATE` or deterministic deduplication keys).
   - *Bulkheads & timeouts*: Every external network call must define explicit timeouts and concurrency limits (`asyncio.Semaphore`).
6. **Performance intuition (orders of magnitude)**:
   - Zero N+1 query loops: Never execute database queries, HTTP calls, or file reads inside loops over records. Batch into `.in_()` queries or bulk inserts.
   - Avoid $O(N^2)$ scans where $O(1)$ dictionary/set lookups apply.
   - Strip heavy columns (e.g. pgvector `embedding` arrays) from read queries via explicit column projections (`[[concepts/vector-egress-stripping]]`).
7. **System design interview rubric**:
   Audit the change through the 5-step System Design Interview lens (Neo Kim & Abdirahman Jama framework in `[[concepts/staff-engineer-verification]]`):
   - *Core Data Mutability & Invariants*: Is data append-only or mutable? What can never be lost? Critical financial state (trades, ledger transactions) must be strictly append-only with compensating records, avoiding destructive `DELETE` operations that sever audit trails.
   - *Query Shape & Index Alignment*: Are new `.eq()`, `.gte()`, or `.order()` queries backed by indexes in `supabase/migrations/`? Ensure queries on growing tables enforce explicit date bounds (`gte`/`lte`), pagination, or `.limit()` to prevent unbounded sequential full-table scans.
   - *End-to-End Data Flow & Caching*: Trace write-to-read lifecycle (background pipeline write -> PostgREST -> TanStack Query cache / query keys -> UI presentation). Verify cache invalidation, staleness bounds (`staleTime`/TTL), and prevent partial-write visibility to concurrent readers.
   - *SPOFs, Bottlenecks & Graceful Degradation*: Identify single points of failure (SPOFs) when external services (local GPU servers, FMP, OpenRouter, Alpaca, PostgREST) stall or return 429/500 errors. Ensure pipelines fail fast or degrade gracefully with fallback without corrupting state.
   - *Tradeoffs & 10x Scale Limits*: Articulate what breaks first under 10x volume, extreme volatility regimes, or concurrent execution.

8. **State-Space Minimization ("Make Illegal States Unrepresentable")**:
   Audit all state representations and lifecycle mutations against `[[concepts/state-machines]]`:
   - *Eliminate Boolean Flag Sprawl*: Never combine multiple boolean flags (`is_loading`, `is_error`, `is_ready`, `has_data`, `is_retrying`) to represent mutually exclusive lifecycle phases ($2^N$ state explosion). Mandate a single discrete enum (`StrEnum`) or TypeScript discriminated union / Python literal union (`State = 'idle' | 'loading' | 'success' | 'error'`).
   - *Make Illegal States Unrepresentable*: Enforce schema and type boundaries so invalid permutations (e.g. `data != null` combined with `error != null`, or `status == "closed"` holding an active order ID) cannot be expressed or queried.
   - *Explicit Transition Matrices & Guards*: Every state mutation must flow through defined transition guards. If an unexpected event occurs, fail fast immediately with an invariant error rather than silently corrupting state.
   - *Derive Rather Than Cache*: Never store duplicate mutable state across components or objects. Derive transient properties from the canonical source of truth on demand.
   - *Implicit State Debt*: Check if the diff touches any implicit state machine listed in `[[concepts/state-machines]]#3-implicit-state-debt--refactoring-backlog` and collapse it into explicit types where feasible.

9. **The 10/10 Agentic Debugging & Cold Subagent Prompts**:

   #### A. Cold-Context Adversarial Reviewer Prompt (for `invoke_subagent`)
   When spawning the `research` subagent for Tier 7 staff review, pass strictly the 1-sentence goal and the diff inside this template:
   ```markdown
   You are an adversarial Staff Software Engineer performing a cold-context code audit.
   Assume the author has conversational sycophancy, patched symptoms, or introduced subtle edge-case bugs.
   
   ### TASK GOAL
   <1-sentence objective of the change>
   
   ### CODE DIFF
   <git diff HEAD~1 or staged/working diff>
   
   ### AUDIT CRITERIA
   1. State Space: Did the change add boolean flag sprawl ($2^N$ states) or allow illegal states? Does it adhere to wiki/concepts/state-machines.md?
   2. Root Cause vs Symptom Patch: Does the diff cure the underlying defect or mask symptoms with loose conditionals?
   3. Invariants & Idempotency: Will re-running this mid-flight duplicate data or corrupt state? Are financial mutations CP-safe?
   4. Complexity & Smells: Does it exceed 10 decision branches (C901), introduce shotgun surgery, or leak abstraction boundaries?
   5. Performance & Leaks: Are there N+1 query loops, unindexed queries, unstripped vector embeddings, or unbounded table scans?
   
   Deliver an uncompromising audit with concrete verdicts: PASS, WARN (Debt Incurred with counterfactual design), or FAIL (blocking defect).
   ```

   #### B. 10/10 Methodical Debugging Protocol (When Tests or Checks Fail)
   If any unit test, typecheck, or verification tier fails during your workflow, **NEVER perform shotgun debugging** (blindly patching lines or adding boolean flags to satisfy the test). Execute this strict 5-step investigative protocol:
   ```markdown
   1. Locate & Reproduce:
      - Pinpoint the exact file and line where failure occurs.
      - Write or isolate a hermetic, minimal reproduction test case that reliably reproduces the failure firsthand (TDD).
   2. Formulate Hypotheses:
      - List 2 to 3 distinct potential root causes before touching production code. Rank them by architectural probability.
   3. Gather Evidence:
      - Trace data flow across boundaries (input validation -> computation -> persistence -> presentation).
      - Inspect variable states and error tracebacks via scratch scripts (Principle 12). Rule hypotheses in or out with concrete evidence.
   4. State-Space & Root Cause Isolation:
      - Identify the exact invalid state, illegal transition, or broken invariant causing the defect.
      - Explain WHY the failure happens rather than just WHAT failed.
   5. Minimal Fix & Proof:
      - Apply the minimal necessary architectural fix. Eliminate the invalid state permanently.
      - Prove the fix hermetically passes all tests with zero artificial sleep and zero external network calls.
   ```

### Tier 8. Wiki and documentation synchronization (MANDATORY)

1. **Synchronize changes everywhere**:
   - When code changes alter formulas, scoring, models, tools, UI components, background tasks, schemas, or architectural patterns, YOU MUST proactively audit and update ALL relevant wiki pages (`wiki/concepts/`, `wiki/entities/`) documenting the new behavior, component interfaces, invariants, and the rationale ("the why"). Never leave new features, model tracks, or schemas undocumented.
2. **Audit all affected surfaces**:
   - Review `git diff --name-only` across backend, frontend, and config to identify every concept and entity page requiring documentation. If a new capability or pattern is introduced, create a new dedicated wiki page.
3. **State machine registry synchronization**:
   - Whenever introducing, modifying, or refactoring a status enum, lifecycle stage, or state transition, update [`wiki/concepts/state-machines.md`](file:///home/cv/Documents/Code/llm-market-bench/wiki/concepts/state-machines.md) to document the new states, ASCII transition flow, and guards.
4. **Refresh code hotspots**:
   - Refresh the code hotspots wiki page via `./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --since "60 days ago" --top 15 --write-wiki`.
5. **Auto-index catalog**:
   - Run `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py --fix` to auto-index new pages into `wiki/index.md`.
6. **Re-index search embeddings**:
   - Update and regenerate QMD vector embeddings via `qmd update && qmd embed` so knowledge remains discoverable via semantic search.
7. **Root-relative paths in backticks**:
   - Any backtick string starting with project prefixes (`apps/`, `packages/`, `scripts/`, `supabase/`, `wiki/`, `.github/`) must be an exact valid path from the repository root. Never use relative shorthand (e.g. `scripts/verify.sh` when the file is at `.agents/skills/verify/scripts/verify.sh`).
8. **Internal link resolution**:
   - Every `[[page-name]]` cross-reference must resolve to an existing markdown page under `wiki/`.
9. **Config parity**:
   - New models in `packages/config/models.json` and tools in `packages/config/tools.json` must be documented in the wiki. Run strict `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py` to ensure zero undocumented tools or models exist.
10. **Auto-wiki preservation mandate and pre-commit emulation**:
   - Staged code changes trigger `.husky/pre-commit` via `scripts/auto-wiki.sh` and `apps/engine/auto_wiki.py`. Ensure existing tools, schemas, and architecture blocks are preserved in related wiki pages. Emulate auto-wiki in dry-run mode (`auto_wiki.py --diff-file <(git diff --cached) --dry-run`) before committing to prevent pre-commit config parity regressions.

---

## 3. Verification report format

Conclude every verification run with an eight-tier status report and a mandatory Staff/Principal critique block:

| Tier | Area | Result | Notes / Action Items |
| :--- | :--- | :--- | :--- |
| **Tier 1** | Static hygiene, LOC ceilings & hotspots | PASS / FAIL | Zero Ruff/Biome warnings; hotspot risk verified |
| **Tier 2** | Builds & types | PASS / FAIL | TypeScript typecheck (`tsc --noEmit`) and production build status |
| **Tier 3** | Hermetic tests & coverage | PASS / FAIL | Pytest / Vitest passing; coverage numbers |
| **Tier 4** | Domain, API & remote DB sanity | PASS / FAIL | Financial bounds, schedule guards, tool parity, migration & edge replica schema cache parity |
| **Tier 5** | Architecture & UI/UX | PASS / FAIL | Zero frontend compute, design system, layout |
| **Tier 6** | Observability | PASS / FAIL | logger.exception used, zero swallowed exceptions |
| **Tier 7** | Staff/Principal critical review | PASS / WARN / FAIL | Subagent verdict, debt incurred, and action items |
| **Tier 8** | Wiki & docs synchronization | PASS / FAIL | Concepts/entities synced, wiki_lint clean, QMD embeddings updated |

### Staff/Principal Engineer Critique
- **Subagent Verdict & Link**: PASS / WARN (Debt Incurred) / FAIL — [<label>](conversation://<conversation-id>)
- **Tactical Defects Caught & Fixed**: <Concrete bugs, bad practices, or principle violations caught by the subagent and resolved during verification>
- **Unresolved Structural Pushback & Fragilities**: <Where the implementation is still flimsy, leaky, or couples too many modules, plus the counterfactual design that would eliminate it>
- **What Breaks First at 10x / Edge Cases**: <Concrete failure modes under re-runs, partial crashes, regime shifts, or 10x scale>
