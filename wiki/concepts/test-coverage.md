---
tags: [testing, quality, policy]
category: concept
---

# Test Coverage Policy

To ensure long-term maintainability and prevent regressions, the project enforces automated test coverage thresholds via pre-commit hooks.

## Thresholds

As of May 2026, the following minimum thresholds are enforced:

| Component | Threshold | Tool |
|-----------|-----------|------|
| **Engine (Python)** | 70% | `pytest-cov` |
| **Web (TypeScript)** | 40% | `vitest` (v8) |

These thresholds are intentionally set near baseline levels to act as a "ratchet"—preventing coverage from decreasing while allowing for gradual improvement.

## Enforcement

Enforcement happens at two levels:

1.  **Local (Pre-commit)**: Controlled by `.husky/pre-commit`. Commits will fail if coverage drops below the threshold.
2.  **CI/CD**: Full test suites run on every PR.

## Configuration

### Engine
Configured via `apps/engine/.coveragerc`. 
- **Omitted**: CLI scripts, migrations, and test files themselves.
- **Exclusions**: `pragma: no cover`, `if TYPE_CHECKING:`, and boilerplate.

### Web
Configured via `apps/web/vitest.config.ts`.
- **Provider**: `v8`
- **Exclusions**: `node_modules`, `dist`, and `.d.ts` files.

## Best Practices

- **Test New Logic**: Every new feature or bug fix must include tests that maintain or increase the coverage percentage.
- **Surgical Exclusions**: Do not exclude core logic to "game" the percentage. Exclusions are reserved for boilerplate and untestable entry points (like `main.py` blocks).
- **Fast Feedback**: The full engine suite contains 725+ tests. While running them sequentially takes ~2.5 minutes, you can run them in parallel via `pytest-xdist` using `./apps/engine/.venv/bin/python3 -m pytest -n auto --cov=. --cov-config=.coveragerc`, which leverages multiple processes to merge coverage and complete the entire suite in ~1m 16s. This high-speed feedback ensures that pre-commit checks remain fast and painless for developer workflows.

## Increasing Thresholds

Thresholds are periodically reviewed and ratcheted upward as the codebase matures.
- **Ratchet Mechanism**: When a component's actual test coverage consistently exceeds the baseline threshold by a significant margin (e.g., 5%+), a task is scheduled to increase the minimum threshold inside `.husky/pre-commit` and update this document accordingly. This prevents coverage regression and drives gradual code quality improvements.
- **Ultimate Goal**: The long-term target is to reach a uniform 80% coverage across all core business-logic components.
