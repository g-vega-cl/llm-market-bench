---
tags: [linter, python, ruff, tooling]
category: entity
---

# Ruff Linter

Ruff is the Python linter and formatter used for the engine (`apps/engine/`). It replaces flake8, isort, and pyupgrade with a single fast Rust-based tool.

## Configuration

Configured in `apps/engine/ruff.toml`:

- **target-version**: py312
- **line-length**: 100
- **Selected rules**: E (pycodestyle errors), F (pyflakes), I (isort), UP (pyupgrade), B (flake8-bugbear), SIM (flake8-simplify)
- **isort known-first-party**: `core`, `analysis`, `autoresearch`, `execution`, `scripts`
- **Format**: double quotes, space indent

## Usage

Lint:
```sh
cd apps/engine && source .venv/bin/activate && ruff check && cd ../..
```

Auto-fix safe issues:
```sh
cd apps/engine && source .venv/bin/activate && ruff check --fix && cd ../..
```

Format:
```sh
cd apps/engine && source .venv/bin/activate && ruff format && cd ../..
```

Runs as part of the pre-commit hook before tests.

## Related

- [[entities/biome-linter]] — TypeScript/JS counterpart
- [[concepts/tool-enforcement]] — code quality enforcement
