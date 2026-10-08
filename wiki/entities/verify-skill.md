---
tags: [verification, skill, testing, linting, agent-tooling]
category: entity
---

# Verify Skill

The **verify skill** (`.agents/skills/verify/`) is the post-coding verification protocol for LLM Market Bench. It is invoked after every coding round or via `/verify` to audit changes against production standards — guaranteeing zero regressions, passing builds, hermetic test isolation, financial and domain sanity, and architectural compliance.

The skill ships as two files:

- `.agents/skills/verify/SKILL.md` — the protocol describing six verification tiers and the required report format.
- `.agents/skills/verify/scripts/verify.sh` — a bundled runner that executes the relevant checks.

## Verification Tiers

The protocol audits every changed file through six tiers; none may be skipped.

1. **Static hygiene, size ceilings & hotspot forensics** — Ruff (E, F, I, UP, B, SIM) and Biome must pass with zero warnings. Enforces a 400-LOC soft ceiling and 800-LOC hard ceiling per file, colocated tests (`foo.py` ↔ `test_foo.py`, `foo.tsx` ↔ `foo.test.tsx`), checks `apps/engine/hotspots.py` for `CRITICAL`/`HIGH` risk files, and **synchronizes the wiki**: updates concepts/entities for changed formulas/models, refreshes `wiki/concepts/code-hotspots.md` via `hotspots.py --write-wiki`, auto-indexes new pages via `wiki_lint.py --fix`, and regenerates QMD vector embeddings (`qmd update && qmd embed`).
2. **Build & type integrity** — `pnpm run typecheck` (`tsc --noEmit`) and `pnpm run build` must pass. Vitest (`pnpm test`) and Biome do not perform type checking because they only transpile; `pnpm run typecheck` is mandatory on all TypeScript changes. Also covers subprocess safety (no compound or multiline `-c` commands), scratch-script usage, and CI workflow secret parity for new `core/config.py` keys.
3. **Hermetic testing & coverage** — Tests must make zero external network calls and pass without ambient environment variables. Engine coverage must stay ≥ 70%, web coverage ≥ 40%. Bug fixes require a failing-without-change regression test.
4. **Domain, API & financial invariants** — Financial bounds checks (implied volatility, spot prices, option deltas, put/call distribution), spot vs futures separation, explicit HTTP 401/403/429/400 handling, weekend and zero-row handling, `America/New_York` timezone enforcement, trade idempotency, FIFO lot matching, short-position prevention, RLS on new migration tables, remote Supabase state parity (verifying migrations via `supabase db push --linked` and confirming new `sys-*` portfolio provisioning online), and tool-definition parity across `tools.json`, `core/llm/tools.py`, `program.md`, and `test_tools_consistency.py`.
5. **Architecture, UI/UX & design system** — Zero frontend compute ([[concepts/zero-frontend-compute]]), consumption of `@llm-market-bench/ui-design-system` components, zero arbitrary Tailwind values, single dark theme, fluent responsive layout with no explicit breakpoints, and tool-first LLM architecture.
6. **Observability & error resilience** — `logger.exception("...")` in `except` blocks ([[concepts/observability-standard]]) and no swallowed errors.

## The Runner

The runner script supports flags to scope the suite:

```sh
./.agents/skills/verify/scripts/verify.sh            # full suite
./.agents/skills/verify/scripts/verify.sh --fast     # lint, format, types, wiki (no builds/tests)
./.agents/skills/verify/scripts/verify.sh --engine   # engine-only
./.agents/skills/verify/scripts/verify.sh --web      # web-only
./.agents/skills/verify/scripts/verify.sh --hotspots # hotspot & churn forensics only
```

It synchronizes the wiki (`hotspots.py --write-wiki`, `wiki_lint.py --fix`, `qmd update && qmd embed`), runs Ruff (`check` and `format --check`), Biome, `hotspots.py`, TypeScript typecheck, the web production build, hermetic pytest with coverage (`--cov-config=.coveragerc`), and web tests with coverage.

## Report Format

Every run concludes with a six-row status table — one row per tier — using PASS / FAIL plus notes and action items.

## Related

- [[concepts/project-linting]]
- [[concepts/code-hotspots]]
- [[concepts/observability-standard]]
- [[concepts/zero-frontend-compute]]
- [[entities/hotspots]]
- [[entities/wiki-linter]]
- [[entities/agent-rules]]
