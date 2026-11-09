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
- **Tier 5: Architecture, UI/UX & design system** — Zero frontend compute ([[concepts/zero-frontend-compute]]), consumption of `@llm-market-bench/ui-design-system` components, zero arbitrary Tailwind values, single dark theme, fluent responsive layout with no explicit breakpoints, and tool-first LLM architecture.
- **Tier 6: Observability & error resilience** — `logger.exception("...")` in `except` blocks ([[concepts/observability-standard]]) and no swallowed errors.
- **Tier 7: Staff/Principal critical code & architecture review** — Rigorous counterfactual audit ("Could this have been done better?"). Enforces mandatory adversarial red-team review by spawning an isolated `research` subagent on the cold git diff to eliminate author bias and sycophancy. Runner script (`verify.sh`) deterministically flags silent exception swallowing (`contextlib.suppress(Exception)`) and shotgun surgery (>10 production files). Audits changes through the 5-step System Design Interview rubric (data mutability/append-only rules, index/query shape alignment, end-to-end data flow and cache invalidation, SPOFs and graceful degradation, and scale limits). Enforces anti-sycophancy (the delete check, comparing against an alternative design, "Tidy First"), SOLID and functional core / imperative shell separation, diff-scoped McCabe cyclomatic complexity (`C901` ≤ 15), explicit CAP/PACELC trade-off stances (CP for ledger/trade mutations, AP for read paths), idempotency, and physical resource intuition (zero N+1 queries, $O(1)$ dictionary lookups). Tactical defects are fixed immediately; structural pushback is escalated in the report. See `[[concepts/staff-engineer-verification]]`.
- **Tier 8: Wiki & documentation synchronization** — **Mandatory sync**: Updates concept and entity pages for any modified formulas, models, tools, schemas, or UI flows. Enforces strict config parity against `packages/config/tools.json` and `packages/config/models.json` via `apps/engine/wiki_lint.py`, preserves existing tool definitions during auto-wiki generation, refreshes `wiki/concepts/code-hotspots.md` via `hotspots.py --write-wiki`, auto-indexes new pages via `wiki_lint.py --fix`, and regenerates QMD vector embeddings (`qmd update && qmd embed`). Guarantees all backtick file references are root-relative and internal wikilinks resolve.

## The Runner

The runner script supports flags to scope the suite:

```sh
./.agents/skills/verify/scripts/verify.sh              # full suite (parallel, -n auto)
./.agents/skills/verify/scripts/verify.sh --sequential # full suite (strictly 1 worker, low CPU/RAM)
./.agents/skills/verify/scripts/verify.sh --fast       # lint, format, types, wiki (no builds/tests)
./.agents/skills/verify/scripts/verify.sh --engine     # engine-only
./.agents/skills/verify/scripts/verify.sh --web        # web-only
./.agents/skills/verify/scripts/verify.sh --hotspots   # hotspot & churn forensics only
```

It synchronizes the wiki (`hotspots.py --write-wiki`, `wiki_lint.py --fix`, `qmd update && qmd embed`), verifies database migration grants and RLS integrity (`apps/engine/tests/test_migration_grants.py`), runs Ruff (`check`, `format --check`, and diff-scoped `C901` complexity), Biome, `hotspots.py`, TypeScript typecheck, the web production build, hermetic pytest with coverage (`--cov-config=.coveragerc`), and web tests with coverage.

## Report Format

Every run concludes with an eight-row status table — one row per tier — using PASS / WARN / FAIL plus notes and action items, followed by a mandatory 4-bullet **Staff/Principal Engineer Critique**:
1. **Subagent Verdict & Link**: `PASS` / `WARN (Debt Incurred)` / `FAIL` with clickable link `[staff-reviewer](conversation://<id>)`
2. **Tactical Defects Caught & Fixed**: Concrete bugs, bad practices, or principle violations caught by the subagent and resolved during verification
3. **Unresolved Structural Pushback & Fragilities**: What is still flimsy, leaky, or coupling too many modules, and what counterfactual design would eliminate it
4. **What Breaks First at 10x / Edge Cases**: Concrete failure modes under re-runs, partial crashes, regime shifts, or 10x scale

## Related

- [[concepts/staff-engineer-verification]]
- [[concepts/project-linting]]
- [[concepts/code-hotspots]]
- [[concepts/observability-standard]]
- [[concepts/zero-frontend-compute]]
- [[entities/hotspots]]
- [[entities/wiki-linter]]
- [[entities/agent-rules]]
