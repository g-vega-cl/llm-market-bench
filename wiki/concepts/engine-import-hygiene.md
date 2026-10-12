---
tags: [engine, ci, imports, convention, python]
category: concept
---

# Engine Import Root Hygiene

Engine production code under `apps/engine/` must import everything relative to the `apps/engine` root — `from core.…`, `from tasks.…`, `from local_autoresearch.…` — and **never** via `from apps.engine.…` or `import apps.engine.…`.

## Why

CI/CD runs engine tests with `working-directory: apps/engine`, so any import that assumes `apps` is on `sys.path` fails with `ModuleNotFoundError: No module named 'apps'`. Running pytest from the repository root can mask the problem because ambient editable `.pth` files quietly put `apps` on the path.

Packages inside `apps/engine` carry `__init__.py` files (e.g. `local_autoresearch/__init__.py`) and `pytest.ini` sets `pythonpath = . ../..` so the engine root and repo root both resolve cleanly.

## Enforcement

- `.agents/skills/verify/scripts/verify.sh` runs `git grep -nE "(from|import) apps\.engine\."` across `core/`, `tasks/`, `execution/`, `analytics/`, `tools/`, and `local_autoresearch/`, failing on any match.
- The verify skill's tier list mirrors this as an explicit hygiene check, and mandates a CI working-directory test parity check (`cd apps/engine && python3 -m pytest -n auto`).

## Related

- [[entities/engine]] — the codebase this applies to
- [[entities/verify-skill]] — enforces the rule
- [[concepts/type-safety]] — sibling code-quality convention
