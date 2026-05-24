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
- **Fast Feedback**: While the full engine suite currently runs in ~30s, focus on keeping tests fast to ensure the pre-commit hook remains useful.

## Increasing Thresholds

Thresholds are periodically reviewed and ratcheted upward as the codebase matures.
- **Ratchet Mechanism**: When a component's actual test coverage consistently exceeds the baseline threshold by a significant margin (e.g., 5%+), a task is scheduled to increase the minimum threshold inside `.husky/pre-commit` and update this document accordingly. This prevents coverage regression and drives gradual code quality improvements.
- **Ultimate Goal**: The long-term target is to reach a uniform 80% coverage across all core business-logic components.
