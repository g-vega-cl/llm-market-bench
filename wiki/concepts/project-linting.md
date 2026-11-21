---
tags: [linting, tooling, code-quality]
category: concept
---

# Project Linting

## Overview

The project enforces code quality through two linters, both wired into the pre-commit hook.

## Linters

### Ruff (Python — `apps/engine/`)

- **Config**: `apps/engine/ruff.toml`
- **Target**: Python 3.12
- **Rules**: E (pycodestyle errors), F (pyflakes), I (isort), UP (pyupgrade), B (flake8-bugbear), SIM (flake8-simplify), C901 (McCabe cyclomatic complexity)
- **Line length**: 120
- **Global ignores**: E501 (line length — individual violations suppressed; 120 char limit acts as a soft guide via ruff format)
- **McCabe complexity ceiling**: `[lint.mccabe] max-complexity = 15` — any function with more than 15 decision points fails `ruff check` across the whole engine, not just changed lines
- **Per-file ignores**:
  - `scripts/*.py` — E402 (sys.path manipulation for executable scripts)
  - `tests/*.py` — SIM117 (nested `with` often clearer in test setup)
  - `tests/test_concurrency_invariants.py` — B023 (closures called within same iteration, false positive)
- **Installed**: In `apps/engine/.venv/`, pinned in `requirements.txt`

Commands:
```sh
# Lint
./apps/engine/.venv/bin/ruff check apps/engine/

# Complexity-only pass
./apps/engine/.venv/bin/ruff check apps/engine/ --select C901

# Auto-fix safe issues
./apps/engine/.venv/bin/ruff check --fix apps/engine/

# Auto-fix all (including unsafe renames, nested-with collapse)
./apps/engine/.venv/bin/ruff check --fix --unsafe-fixes apps/engine/

# Format
./apps/engine/.venv/bin/ruff format apps/engine/
```

### Biome (TypeScript — `apps/web/`, `packages/`)

- **Config**: `biome.json` (root)
- **Rules**: Recommended + organize imports; `noExplicitAny` is set to `error`. `noExcessiveCognitiveComplexity`, `noNonNullAssertion`, `noArrayIndexKey`, `noStaticElementInteractions`, `useKeyWithClickEvents`, `noLabelWithoutControl` are downgraded to `warn`.
- **Style**: Single quotes, semicolons, trailing commas, 4-space indent, 100 line width
- **Installed**: Root devDependency (`@biomejs/biome`)

Commands:
```sh
# Lint + format check
pnpm biome check

# Auto-fix safe issues
pnpm biome check --write

# Auto-fix all (including unsafe: removes unused imports with side effects)
pnpm biome check --write --unsafe
```

### Wiki Linters (`apps/engine/`)

- **Structural Lint (`apps/engine/wiki_lint.py`)**: Runs on pre-commit when `wiki/` or `raw/` files change. Validates frontmatter completeness, broken wiki links, orphan pages, index coverage, codebase path references, and configuration parity against `packages/config/models.json` and `packages/config/tools.json`. Runs in ~20ms in pure Python.
- **Git Drift Auditor (`apps/engine/wiki_lint_llm.py`)**: Runs weekly on Saturday 10:00 AM ET via `.github/workflows/wiki-lint.yml`. Queries `git log --since="7 days ago"`, maps modified code/config files to the corresponding 5-8 wiki pages, and checks for code-documentation drift against an explicit rubric. Exits in 0.5s if no functional code changed that week.

### Zero-Warning Test Enforcement

- **Python (`pytest.ini`)**: Configured at repository root and `apps/engine/` to filter third-party deprecation warnings (e.g. `websockets.legacy`). Both files also declare `norecursedirs = .venv market __pycache__ .git node_modules`, so a bare `pytest` invocation never descends into the virtualenv, the local `market` data directory, or `node_modules`.
- **Web (`apps/web/package.json`)**: Configured with `NODE_OPTIONS="--no-warnings --no-deprecation"` to suppress experimental Node.js runtime warnings during test runs.

## Pre-commit Hook

`.husky/pre-commit` uses `set -euo pipefail` for fail-fast behavior. It is **staged-file scoped**: the hook classifies the staged paths once and runs only the checks those paths can break, so a docs-only or single-file commit no longer pays for the entire suite.

### Staged file collection

```sh
mapfile -t STAGED_FILES < <(git diff --cached --name-only --diff-filter=ACMR)
```

`--diff-filter=ACMR` skips deletions, so removing a file never feeds a nonexistent path to Ruff, Biome, or pytest.

### Execution order

1. `secret_scanner.py --cached` — fail-fast credential scan (blocking)
2. `scripts/auto-wiki.sh` — wiki generation (blocking)
3. Ruff on the staged engine Python files
4. Engine pytest — full suite or targeted subset
5. Root-level tests (`tests/test_*.py`, `tests/*_test.py`, `tests/verify_*.py`)
6. `apps/free_llm_proxy` test suite
7. Biome on the staged web/package files
8. `pnpm --filter web typecheck`
9. Web vitest — full suite or `vitest related`
10. `packages/mcp-knowledge-rag` Biome + test suite
11. Wiki lint + QMD re-index (conditional on `wiki/` or `raw/` changes)

### Scoping rules

| Staged path | Effect |
| :--- | :--- |
| `apps/engine/**/*.py` | Ruff on those files. `core/*`, `execution/*`, `tests/conftest.py`, `apps/engine/pytest.ini`, or `packages/config/*` escalate to the **full** engine suite; otherwise the hook collects matching test files (`tests/test_*<base>*.py`, same-subdirectory `test_*.py`/`*_test.py` globs) and runs only those. If nothing matches, pytest is skipped with a hint to run `verify.sh`. |
| `tests/test_*.py`, `tests/*_test.py`, `tests/verify_*.py` | Run directly from the repo root. |
| `apps/free_llm_proxy/*` | Runs `apps/free_llm_proxy/tests/`. |
| `packages/config/*` | Escalates to the full engine suite **and** the full web suite. |
| `apps/web/*` | Biome on the staged files. `apps/web/src/test/*`, `apps/web/package.json`, `vitest.config.ts`, `vite.config.ts` escalate to the full web suite; other `apps/web/src/*` files run `vitest related --run` on the changed sources. |
| `packages/database/*`, `packages/ui-design-system/*` | Biome + full web suite. |
| `packages/mcp-knowledge-rag/*` | Biome + that package's own test suite. |
| `wiki/*`, `raw/*` | Structural wiki lint + `qmd update` / `qmd embed`. |

### Design and contrast static audits

When a staged `apps/web` file is a `.ts`/`.tsx` source file, the hook additionally runs `src/test/contrast-audit.test.tsx` and `src/test/design-variant-budget.test.tsx` after the related tests, so a styling change can never slip past the [[concepts/design-variant-budget]] and contrast invariants.

### Worker caps and sequential mode

- **Engine**: `pytest -n 4` for the full suite, `pytest -n 4 <targets>` for a targeted run, and plain in-process `pytest` when sequential mode is on or only one target matched.
- **Web**: `--maxWorkers=4` by default, `--maxWorkers=1` in sequential mode. The flag is passed directly to `pnpm test` / `pnpm exec vitest` — never behind an extra `--`, which pnpm would forward as a literal argument.
- **Sequential toggle**: `SEQUENTIAL=1 git commit` or `git config benchify.sequential true`.

The 4-worker caps are pinned by `apps/engine/tests/test_pre_commit_sequential.py`, which asserts the hook contains `-n 4` (and not unbounded `-n auto`), sets `WEB_WORKERS=1` in sequential mode, and never emits an extra `--` before `--maxWorkers` under pnpm.

The verify runner mirrors the same cap: `.agents/skills/verify/scripts/verify.sh` runs `pytest -n 4` and `pnpm test --maxWorkers=4`, keeps `--sequential` as a 1-worker escape hatch, and is pinned by `apps/engine/tests/test_verify_skill.py` (no `-n auto`, caps present). CI is the only place that still uses `-n auto`, because it runs on dedicated runners.

### What moved out of pre-commit

- **Coverage gates** — the hook no longer passes `--cov` / `--cov-fail-under`. Coverage is enforced by `.agents/skills/verify/scripts/verify.sh` and CI (see [[concepts/test-coverage]]).
- **`pnpm build:web`** — the production build (`vite build && tsc --noEmit`) now runs in the CI `test-web` job. The hook still runs `pnpm --filter web typecheck` so type regressions fail locally.

## CI Workflow

`.github/workflows/ci.yml` (name `CI`, `permissions: contents: read`) runs two jobs on every push and pull request:

| Job | Steps |
| :--- | :--- |
| `test` (engine) | Checkout, Python setup, dependency install, `python3 -m pytest -n auto` from `apps/engine`. |
| `test-web` (15-minute timeout) | Checkout, `pnpm/action-setup@v4`, Node 24 with pnpm cache, `pnpm install --frozen-lockfile`, `pnpm biome check`, `pnpm --filter web typecheck`, `pnpm --filter web test --maxWorkers=2`, `pnpm build:web`. |

CI is the authoritative full-suite gate; the pre-commit hook is the fast local filter.

## TypeScript type conventions

- **`Record<string, any>`** — preferred for Supabase JSONB/metadata columns. Avoids TanStack Start `createServerFn` deep inference issues AND allows component-level access without `as any` casts.
  > [!IMPORTANT]
  > Since `noExplicitAny` is configured as a blocking `error` in `biome.json` with no global/wildcard overrides, using `Record<string, any>` requires an inline suppression comment:
  > `// biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization`
- **`Record<string, unknown>`** — acceptable for intermediate types where data is never deeply accessed in JSX, but must be converted to `Record<string, any>` if it flows through a `createServerFn` handler.
- **`unknown`** — for truly dynamic API response types where the shape is unknowable.

### TanStack Start `createServerFn` deep type inference pitfall

`createServerFn().handler()` applies a serialization type transform that rewrites index signatures deep in the return type, expanding `Record<string, unknown>` → `{ [x: string]: {} }`. This is fundamentally incompatible with database types (like `Memory`, `LLMReasoningLog`, `Decision`) that use `Record<string, unknown>` for JSONB/metadata fields.

**Fix**: Change database JSONB/metadata fields from `Record<string, unknown>` to `Record<string, any>` in `packages/database/index.ts`. This is semantically equivalent for JSON-serializable Supabase data and fixes ALL route files at once. (Requires inline `// biome-ignore lint/suspicious/noExplicitAny` suppressions on the type declarations).

**Workaround** (if type change is undesirable): Use `(createServerFn({ method: 'GET' }) as any)` on the `createServerFn` call, which bypasses the deep type inference entirely. Must be applied to each affected route file, accompanied by a `// biome-ignore lint/suspicious/noExplicitAny` inline comment to pass pre-commit checks.

## See Also

- [[entities/wiki-linter]] — Detailed wiki linting (structural + LLM)
- [[entities/ruff-linter]] — Python linter details
- [[entities/biome-linter]] — TypeScript/JS linter details
- [[concepts/code-hotspots]] — Churn forensics and bug hotspot analyzer
- [[concepts/test-coverage]] — where the coverage gates now live
- [[concepts/test-latency-guards]] — why the engine suite stays fast under parallel workers
- [[entities/engine]]
- `AGENTS.md` — canonical command reference
