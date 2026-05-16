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
- **Rules**: E (pycodestyle errors), F (pyflakes), I (isort), UP (pyupgrade), B (flake8-bugbear), SIM (flake8-simplify)
- **Line length**: 120
- **Global ignores**: E501 (line length — individual violations suppressed; 120 char limit acts as a soft guide via ruff format)
- **Per-file ignores**:
  - `scripts/*.py` — E402 (sys.path manipulation for executable scripts)
  - `tests/*.py` — SIM117 (nested `with` often clearer in test setup)
  - `tests/test_concurrency_invariants.py` — B023 (closures called within same iteration, false positive)
- **Installed**: In `apps/engine/venv/`, pinned in `requirements.txt`

Commands:
```sh
# Lint
./apps/engine/venv/bin/ruff check apps/engine/

# Auto-fix safe issues
./apps/engine/venv/bin/ruff check --fix apps/engine/

# Auto-fix all (including unsafe renames, nested-with collapse)
./apps/engine/venv/bin/ruff check --fix --unsafe-fixes apps/engine/

# Format
./apps/engine/venv/bin/ruff format apps/engine/
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

## Pre-commit Hook

`.husky/pre-commit` uses `set -euo pipefail` for fail-fast behavior. Key design decisions:

- **Subshells for directory isolation** — `( cd "$REPO_ROOT/apps/engine" && source .venv/bin/activate && ruff check )` instead of `cd apps/engine && ... && cd ../..`. If a command fails, the subshell exits cleanly and the parent CWD is unchanged.
- **Absolute paths from `$REPO_ROOT`** — `REPO_ROOT="$(git rev-parse --show-toplevel)"` at the top, then reference everything as `$REPO_ROOT/path/to/thing`.
- **Non-blocking steps use `|| true`** — auto-wiki only. Biome lint was historically non-blocking due to pre-existing errors but those are now resolved (0 warnings as of 2026-05-14).
- **`pnpm build:web` is ALWAYS blocking** — `vite build && tsc --noEmit` must pass. Never weaken this with `|| true`.
- **Tests are blocking** — `pytest` (engine) and `vitest` (web) must pass.

### Execution order

1. `scripts/auto-wiki.sh` (non-blocking)
2. Ruff lint — engine Python (fail-fast)
3. Biome lint — web TypeScript (non-blocking for historical reasons; 0 warnings as of 2026-05-14, can be made blocking)
4. Engine tests — pytest (fail-fast)
5. Web tests — vitest (fail-fast)
6. Web build — `vite build && tsc --noEmit` (fail-fast, MUST pass)
7. Wiki lint + QMD re-index (conditional on wiki/raw changes, fail-fast)

## TypeScript type conventions

- **`Record<string, any>`** — preferred for Supabase JSONB/metadata columns. Avoids TanStack Start `createServerFn` deep inference issues AND allows component-level access without `as any` casts.
- **`Record<string, unknown>`** — acceptable for intermediate types where data is never deeply accessed in JSX, but must be converted to `Record<string, any>` if it flows through a `createServerFn` handler.
- **`unknown`** — for truly dynamic API response types where the shape is unknowable.

### TanStack Start `createServerFn` deep type inference pitfall

`createServerFn().handler()` applies a serialization type transform that rewrites index signatures deep in the return type, expanding `Record<string, unknown>` → `{ [x: string]: {} }`. This is fundamentally incompatible with database types (like `Memory`, `LLMReasoningLog`, `Decision`) that use `Record<string, unknown>` for JSONB/metadata fields.

**Fix**: Change database JSONB/metadata fields from `Record<string, unknown>` to `Record<string, any>` in `packages/database/index.ts`. This is semantically equivalent for JSON-serializable Supabase data and fixes ALL route files at once.

**Workaround** (if type change is undesirable): Use `(createServerFn({ method: 'GET' }) as any)` on the `createServerFn` call, which bypasses the deep type inference entirely. Must be applied to each affected route file.

## See Also

- [[entities/ruff-linter]] — Python linter details
- [[entities/biome-linter]] — TypeScript/JS linter details
- [[entities/engine]]
- `AGENTS.md` — canonical command reference