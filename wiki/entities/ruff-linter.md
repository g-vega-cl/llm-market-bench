---
tags: [linter, python, ruff, tooling]
category: entity
---

# Ruff Linter

Ruff is the Python linter and formatter used for the engine (`apps/engine/`). It replaces flake8, isort, and pyupgrade with a single fast Rust-based tool.

## Configuration

Configured in `apps/engine/ruff.toml`:

- **target-version**: py312
- **line-length**: 120
- **Selected rules**: E (pycodestyle errors), F (pyflakes), I (isort), UP (pyupgrade), B (flake8-bugbear), SIM (flake8-simplify), C901 (McCabe cyclomatic complexity)
- **Global ignores**: E501 (line length — ruff format handles wrapping; remaining violations are intentional)
- **McCabe complexity**: `[lint.mccabe] max-complexity = 15` — functions exceeding 15 decision points are lint errors across the entire engine, enforcing the per-function ceiling from [[concepts/staff-engineer-verification]]
- **Per-file ignores**: `scripts/*.py` = [E402], `tests/*.py` = [SIM117], `tests/test_concurrency_invariants.py` = [B023]
- **isort known-first-party**: `core`, `analysis`, `autoresearch`, `execution`, `scripts`
- **Format**: double quotes, space indent

## Installation

Ruff is installed in the engine virtual environment:

```sh
apps/engine/.venv/bin/pip install ruff
```

If the pre-commit hook fails with `ruff: command not found`, reinstall it. The pre-commit hook activates the venv before running ruff, so ruff must be present in `apps/engine/.venv/bin/`.

## Usage

Lint:
```sh
cd apps/engine && source .venv/bin/activate && ruff check && cd ../..
```

Complexity-only pass:
```sh
cd apps/engine && source .venv/bin/activate && ruff check --select C901 && cd ../..
```

Auto-fix safe issues:
```sh
cd apps/engine && source .venv/bin/activate && ruff check --fix && cd ../..
```

Format:
```sh
cd apps/engine && source .venv/bin/activate && ruff format && cd ../..
```

Runs as part of the pre-commit hook before tests. `apps/engine/tests/test_verify_skill.py` asserts both the `C901` selection and the `max-complexity = 15` setting, and runs `ruff check --select C901` over the whole engine to guarantee zero complexity violations.

## Related

- [[entities/biome-linter]] — TypeScript/JS counterpart
- [[concepts/project-linting]] — pre-commit hook design
- [[concepts/staff-engineer-verification]] — cyclomatic complexity ceilings
- [[concepts/tool-enforcement]] — code quality enforcement
