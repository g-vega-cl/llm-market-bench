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
- **Rules**: E (pycodestyle), F (pyflakes), I (isort), UP (pyupgrade), B (flake8-bugbear), SIM (flake8-simplify)
- **Line length**: 100
- **Installed**: In `apps/engine/venv/`, pinned in `requirements.txt`

Commands:
```sh
# Lint
./apps/engine/venv/bin/ruff check apps/engine/

# Auto-fix safe issues
./apps/engine/venv/bin/ruff check --fix apps/engine/

# Format
./apps/engine/venv/bin/ruff format apps/engine/
```

### Biome (TypeScript — `apps/web/`, `packages/`)

- **Config**: `biome.json` (root)
- **Rules**: Recommended + organize imports
- **Style**: Single quotes, semicolons, trailing commas, 4-space indent, 100 line width
- **Installed**: Root devDependency (`@biomejs/biome`)

Commands:
```sh
# Lint + format check
pnpm biome check

# Auto-fix all
pnpm biome check --write
```

## Pre-commit Hook

`.husky/pre-commit` runs in this order:

1. Auto-wiki script (non-blocking)
2. `ruff check` (fail-fast)
3. `pnpm biome check` (fail-fast)
4. `pytest` (engine)
5. `pnpm test` (web)
6. `pnpm build:web` (type-check)
7. Wiki lint + QMD re-index (conditional on wiki/raw changes)

## See Also

- [[entities/ruff-linter]] — Python linter details
- [[entities/biome-linter]] — TypeScript/JS linter details
- [[entities/engine]]
- `AGENTS.md` — canonical command reference
