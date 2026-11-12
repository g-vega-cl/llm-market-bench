---
tags: [verification, skill, testing, linting, agent-tooling]
category: entity
---

# Verify Skill

The **verify skill** (`.agents/skills/verify/`) is the post-coding verification protocol for LLM Market Bench. It is invoked after every coding round or via `/verify` to audit changes against production standards — guaranteeing zero regressions, passing builds, hermetic test isolation, financial and domain sanity, architectural compliance, and staff/principal engineer code quality.

The skill ships as two files:

- `.agents/skills/verify/SKILL.md` — the protocol describing eight verification tiers and the required report format.
- `.agents/skills/verify/scripts/verify.sh` — a bundled runner that executes the relevant checks.

## Verification Tiers

The protocol audits every changed file through eight tiers; none may be skipped.

- **Tier 1: Static hygiene, size ceilings & hotspot forensics** — Ruff (E, F, I, UP, B, SIM) and Biome must pass with zero warnings. Enforces a 400-LOC soft ceiling and 800-LOC hard ceiling per file, colocated tests (`foo.py` ↔ `test_foo.py`, `foo.tsx` ↔ `foo.test.tsx`), checks `apps/engine/hotspots.py` for `CRITICAL`/`HIGH` risk files, and validates engine production import root hygiene.
- **Tier 2: Build & type integrity** — `pnpm run typecheck` (`tsc --noEmit`) and `pnpm run build` must pass. Vitest (`pnpm test`) and Biome do not perform type checking because they only transpile; `pnpm run typecheck` is mandatory on all TypeScript changes. Also covers subprocess safety (no compound or multiline `-c` commands), scratch-script usage, and CI workflow secret parity for new `core/config.py` keys.
- **Tier 3: Hermetic testing & coverage** — Tests must make zero external network calls and pass without ambient environment variables. Engine coverage must stay ≥ 70%, web coverage ≥ 40%. Bug fixes require a failing-without-change regression test.
- **Tier 4: Domain, API & financial invariants** — Financial bounds checks (implied volatility, spot prices, option deltas, put/call distribution), spot vs futures separation, explicit HTTP 401/403/429/400 handling, weekend and zero-row handling, `America/New_York` timezone enforcement, trade idempotency, FIFO lot matching, short-position prevention, RLS on new migration tables, self-hosted PostgreSQL and PostgREST schema parity (verifying migrations hermetically via `apps/engine/tests/test_migration_grants.py` and confirming new `sys-*` portfolio provisioning online), and tool-definition parity across `tools.json`, `core/llm/tools.py`, `program.md`, and `test_tools_consistency.py`.
  - **Secondary edge replica & PostgREST schema reload (MANDATORY on migrations)** — Physical streaming replication on the MiniPC edge replica (`cv-minipc@minipc`) does **not** forward PostgreSQL `NOTIFY` events (`NOTIFY pgrst, 'reload schema'`), and the standby PostgREST runs with `PGRST_DB_CHANNEL_ENABLED: false`. Because `docker/archive/nginx.secondary.conf` routes all `GET` read queries directly to the MiniPC PostgREST instance, leaving the replica un-restarted causes silent `PGRST205: Could not find table ... in schema cache` failures on public web read paths (`https://benchify-archive-db.clvg.uk`). Whenever migrations are created or applied, the agent MUST deploy to the MiniPC edge node:
    bash
    ./docker/archive/deploy_secondary.sh cv-minipc@minipc
    
    (which syncs configs, executes `docker compose restart archive-postgrest` on the replica to force a schema cache reload, and probes local read health). Then execute a live read probe against `SUPABASE_PROJECT_URL` (`https://benchify-archive-db.clvg.uk/rest/v1/<new_or_modified_table>?limit=1`) to confirm `200 OK` and zero `PGRST205` errors.
- **Tier 5: Architecture, UI/UX & design system** — Zero frontend compute ([[concepts/zero-frontend-compute]]), consumption of `@llm-market-bench/ui-design-system` components, zero arbitrary Tailwind values, single dark theme, fluent responsive layout with no explicit breakpoints, and tool-first LLM architecture.
- **Tier 6: Observability & error resilience** — `logger.exception("...")` in `except` blocks ([[concepts/observability-standard]]) and no swallowed errors.
- **Tier 7: Staff/Principal critical code & architecture review** — Rigorous counterfactual audit ("Could this have been done better?"). Enforces mandatory adversarial red-team review by spawning an isolated `research` subagent on the cold git diff using the cold-context prompt template to eliminate author bias and sycophancy. The subagent is delegated through the host agent platform's native tool — `invoke_subagent` (`TypeName: "research"`, `Role: "Staff Engineer Reviewer"`) on Antigravity, or `delegate_task` on Hermes — so the protocol stays portable across agent runtimes. Mandates state-space minimization ("make illegal states unrepresentable", banning $2^N$ boolean flag sprawl, requiring explicit state transition matrices, and deriving state over caching mutable state). Enforces the 10/10 Methodical Agentic Debugging Protocol (5-step investigative loop: locate/reproduce -> hypotheses -> evidence -> state isolation -> minimal fix) to eliminate shotgun debugging. Runner script (`verify.sh`) deterministically flags silent exception swallowing (`contextlib.suppress(Exception)`) and shotgun surgery (>10 production files). Audits changes through the 5-step System Design Interview rubric (data mutability/append-only rules, index/query shape alignment, end-to-end data flow and cache invalidation, SPOFs and graceful degradation, and scale limits). Enforces anti-sycophancy (the delete check, comparing against an alternative design, "Tidy First"), SOLID and functional core / imperative shell separation, diff-scoped McCabe cyclomatic complexity (`C901` ≤ 15), explicit CAP/PACELC trade-off stances (CP for ledger/trade mutations, AP for read paths), idempotency, and physical resource intuition (zero N+1 queries, $O(1)$ dictionary lookups). Tactical defects are fixed immediately; structural pushback is escalated in the report. See `[[concepts/staff-engineer-verification]]` and `[[concepts/state-machines]]`.
- **Tier 8: Wiki & documentation synchronization** — **Mandatory sync**: Updates concept and entity pages for any modified formulas, models, tools, schemas, state machines, or UI flows. Enforces state machine synchronization against `[[concepts/state-machines]]`. Enforces strict config parity against `packages/config/tools.json` and `packages/config/models.json` via `apps/engine/wiki_lint.py`, preserves existing tool definitions during auto-wiki generation, refreshes `wiki/concepts/code-hotspots.md` via `hotspots.py --write-wiki`, auto-indexes new pages via `wiki_lint.py --fix`, and regenerates QMD vector embeddings (`qmd update && qmd embed`). Guarantees all backtick file references are root-relative and internal wikilinks resolve.

## The Runner

The runner script supports flags to scope the suite:

sh
./.agents/skills/verify/scripts/verify.sh              # full suite (parallel, -n auto)
./.agents/skills/verify/scripts/verify.sh --sequential # full suite (strictly 1 worker, low CPU/RAM)
./.agents/skills/verify/scripts/verify.sh --fast       # lint, format, types, wiki (no builds/tests)
./.agents/skills/verify/scripts/verify.sh --engine     # engine-only
./.agents/skills/verify/scripts/verify.sh --web        # web-only
./.agents/skills/verify/scripts/verify.sh --hotspots   # hotspot & churn forensics only


It synchronizes the wiki (`hotspots.py --write-wiki`, `wiki_lint.py --fix`, `qmd update && qmd embed`), verifies database migration grants and RLS integrity (`apps/engine/tests/test_migration_grants.py`), runs Ruff (`check`, `format --check`, and diff-scoped `C901` complexity), Biome, `hotspots.py`, TypeScript typecheck, the web production build, hermetic pytest with coverage (`--cov-config=.coveragerc`), and web tests with coverage.

### Subagent Delegation Across Agent Runtimes

Tier 7's adversarial review depends on spawning a cold-context `research` subagent, but the delegation primitive differs per host platform. The skill protocol names both: `invoke_subagent` on Antigravity (parameterized with `TypeName: "research"` and `Role: "Staff Engineer Reviewer"`), and `delegate_task` on Hermes. Only the 1-sentence goal plus the git diff is passed through the cold-context prompt template — no justifications, no rationalizations.

### Migration Detection & Edge Replica Reminder

When `supabase/migrations/` exists, the runner additionally inspects `git diff --name-only HEAD~1 HEAD -- supabase/migrations/` and `git status --porcelain -- supabase/migrations/`. If any migration was touched in the recent commit or is dirty in the working tree, it prints a `[DATABASE / REPLICA MANDATE]` notice explaining that physical streaming replication does not propagate `NOTIFY` events, that the standby PostgREST does not auto-reload its schema cache without a container restart, and that the operator must run `./docker/archive/deploy_secondary.sh cv-minipc@minipc` and verify a live read probe against `SUPABASE_PROJECT_URL` with zero `PGRST205` errors. See [[entities/secondary-minipc-edge]] and [[concepts/hybrid-database-archival]].

### QMD Embed Failure Tolerance

`qmd embed` runs with its output captured to a temp file. A failure whose output matches a GPU VRAM constraint (`cuda error` or `out of memory`) is downgraded to a warning — the run continues, and BM25 keyword search remains fully updated because `qmd update` already completed. Any other `qmd embed` failure prints the captured output to stderr and aborts the run with a non-zero exit, so genuine embedding regressions are never silently swallowed.

## Report Format

Every run concludes with an eight-row status table — one row per tier — using PASS / WARN / FAIL plus notes and action items, followed by a mandatory 4-bullet **Staff/Principal Engineer Critique**:
1. **Subagent Verdict & Link**: `PASS` / `WARN (Debt Incurred)` / `FAIL` with clickable link `[staff-reviewer](conversation://<id>)`
2. **Tactical Defects Caught & Fixed**: Concrete bugs, bad practices, or principle violations caught by the subagent and resolved during verification
3. **Unresolved Structural Pushback & Fragilities**: What is still flimsy, leaky, or coupling too many modules, and what counterfactual design would eliminate it
4. **What Breaks First at 10x / Edge Cases**: Concrete failure modes under re-runs, partial crashes, regime shifts, or 10x scale

## Related

- [[concepts/state-machines]]
- [[concepts/staff-engineer-verification]]
- [[concepts/project-linting]]
- [[concepts/code-hotspots]]
- [[concepts/observability-standard]]
- [[concepts/zero-frontend-compute]]
- [[entities/hotspots]]
- [[entities/wiki-linter]]
- [[entities/agent-rules]]
- [[entities/secondary-minipc-edge]]
- [[concepts/hybrid-database-archival]]
