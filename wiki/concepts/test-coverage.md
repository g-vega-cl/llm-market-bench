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

1.  **Local (Pre-commit)**: Controlled by `.husky/pre-commit`. Commits will fail if coverage drops below the threshold. Supports sequential 1-worker mode to reduce CPU and RAM usage via `SEQUENTIAL=1 git commit` or permanently via `git config benchify.sequential true`.
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

## Hermetic Testing & Zero-Network Policy (MANDATORY)

All tests in the repository must be 100% hermetic:
- **No Outbound Network Calls**: Tests must never initiate live HTTP requests, WebSocket connections, or external socket calls to third-party services (FMP, Massive/Polygon, FRED, Alpaca, Supabase, LLM provider APIs, or Gmail IMAP).
- **Socket & DNS Enforcement**: `apps/engine/tests/conftest.py` installs a global, session-scoped network guard fixture (`block_external_network_calls`). Any attempt to resolve external DNS or open a non-loopback TCP connection immediately raises a `RuntimeError`, failing the test fast before network packets leave the machine.
- **Credential Independence**: Tests must never rely on ambient environment variables (`FMP_API_KEY`, `OPENAI_API_KEY`, etc.). When testing functions that check API keys, tests must explicitly mock or patch the key (e.g. `patch("tools.congress_tools.FMP_API_KEY", "test-key")`), ensuring tests pass reliably in clean CI runners.

## Zero Artificial Sleep & Test Latency Policy (MANDATORY)

Test suites must execute cleanly without artificial delays. Slow tests cannot be solved simply by adding parallel compute processes (`pytest -n auto`) if individual tests block on real-time sleeps, rate limiters, or retry backoffs.

- **Zero Unmocked Tenacity Retries**: Tenacity `@retry` decorators must specify exception filters (`retry_if_exception`) to fast-fail non-transient errors (such as `RuntimeError` from the hermetic socket guard or 401/403 HTTP errors) rather than retrying with exponential backoff (e.g., 4s + 4s + 8s). Tests asserting retry behavior must patch retry sleep (`patch.object(func.retry, "sleep", return_value=None)`).
- **Autouse Rate Limiter & Embedding Fixtures**: Global singletons (like `_MASSIVE_LIMITER` in `apps/engine/execution/market_data.py`) must be neutralized in `apps/engine/tests/conftest.py` via autouse fixtures (`hermetic_massive_rate_limiter`, `hermetic_memory_store_embeddings`) so tests never wait for token bucket replenishment.
- **Environment-Aware Fallback Delays**: Any loop or fallback logic that sleeps on transient connection failure (e.g. local autoresearch server checks) must detect `os.getenv("PYTEST_CURRENT_TEST")` and set delay to 0.0 seconds.
- **Latency Regression Suite**: `apps/engine/tests/test_test_suite_latency_guards.py` validates that rate-limited, retried, and fallback code paths execute in under 100ms.

See [[concepts/test-latency-guards]] for the detailed architectural breakdown.

## Related

- [[concepts/test-latency-guards]]
- [[sources/engine-testing-source]]
- [[sources/web-testing-source]]


