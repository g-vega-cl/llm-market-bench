---
tags: [testing, quality, policy]
category: concept
---

# Test Coverage Policy

To ensure long-term maintainability and prevent regressions, the project enforces automated test coverage thresholds.

## Thresholds

As of May 2026, the following minimum thresholds are enforced:

| Component | Threshold | Tool |
|-----------|-----------|------|
| **Engine (Python)** | 70% | `pytest-cov` |
| **Web (TypeScript)** | 40% | `vitest` (v8) |

These thresholds are intentionally set near baseline levels to act as a "ratchet"—preventing coverage from decreasing while allowing for gradual improvement.

## Enforcement

Enforcement happens at two levels, neither of which is the pre-commit hook:

1.  **Verify skill (local, full)**: `.agents/skills/verify/scripts/verify.sh` runs the hermetic pytest suite with `--cov=. --cov-config=.coveragerc` and the web suite with coverage, failing the run when a threshold regresses. Both suites default to a 4-worker cap (`pytest -n 4`, `pnpm test --maxWorkers=4`), matching `.husky/pre-commit`; `verify.sh --sequential` drops the whole run to 1 worker for low-memory hosts.
2.  **CI/CD**: `.github/workflows/ci.yml` runs the engine suite (`pytest -n auto`) and the `test-web` job (`biome check`, `typecheck`, `vitest --maxWorkers=2`, `pnpm build:web`) on every push and pull request.

The pre-commit hook deliberately runs **scoped, worker-capped tests without coverage** (`pytest -n 4` on affected or core engine tests, `vitest related --maxWorkers=4`) so commits stay fast; the coverage ratchet is a verify/CI concern. See [[concepts/project-linting]] for the full hook scoping rules.

### Worker Cap Policy

Local test execution is capped at 4 workers everywhere — `.husky/pre-commit`, `.agents/skills/verify/scripts/verify.sh`, and the commands documented in `GEMINI.md` and `.agents/skills/verify/SKILL.md`. Unbounded `pytest -n auto` and an unpinned `pnpm test` are prohibited locally so a full verify cannot starve the host. `--sequential` (or `SEQUENTIAL=1 git commit`) is the deliberate low-memory escape hatch and forces 1 worker end to end. CI is the only place that still uses `-n auto`, because it runs on dedicated runners.

## Configuration

### Engine
Configured via `apps/engine/.coveragerc`. 
- **Omitted**: CLI scripts, migrations, and test files themselves.
- **Exclusions**: `pragma: no cover`, `if TYPE_CHECKING:`, and boilerplate.
- **Collection scope**: both `pytest.ini` files (repo root and `apps/engine/`) declare `norecursedirs = .venv market __pycache__ .git node_modules`, so a bare `pytest` run never collects from the virtualenv, the local `market` data directory, or `node_modules`.

### Web
Configured via `apps/web/vitest.config.ts`.
- **Provider**: `v8`
- **Exclusions**: `node_modules`, `dist`, and `.d.ts` files.

## Best Practices

- **Test New Logic**: Every new feature or bug fix must include tests that maintain or increase the coverage percentage.
- **High-Signal Tests Only**: Focus unit tests on pure logic, parsers, financial math, state reducers, and API/schema contracts. Never mock the module under test or child page components just to satisfy coverage; mock only external I/O boundaries. Avoid brittle CSS/layout assertions and heavy integration tests — `tsc --noEmit`, Biome, and the static design/hydration audits already cover those surfaces.
- **Surgical Exclusions**: Do not exclude core logic to "game" the percentage. Exclusions are reserved for boilerplate and untestable entry points (like `main.py` blocks).
- **Fast Feedback**: The full engine suite contains 725+ tests. While running them sequentially takes ~2.5 minutes, you can run them in parallel via `pytest-xdist` using `./apps/engine/.venv/bin/python3 -m pytest -n 4 --cov=. --cov-config=.coveragerc`, which leverages multiple processes to merge coverage and completes the entire suite in roughly a minute. This high-speed feedback ensures that pre-commit checks remain fast and painless for developer workflows without saturating the host.

## Increasing Thresholds

Thresholds are periodically reviewed and ratcheted upward as the codebase matures.
- **Ratchet Mechanism**: When a component's actual test coverage consistently exceeds the baseline threshold by a significant margin (e.g., 5%+), a task is scheduled to increase the minimum threshold inside `.agents/skills/verify/scripts/verify.sh` and `.github/workflows/ci.yml`, and update this document accordingly. This prevents coverage regression and drives gradual code quality improvements.
- **Ultimate Goal**: The long-term target is to reach a uniform 80% coverage across all core business-logic components.

## Hermetic Testing & Zero-Network Policy (MANDATORY)

All tests in the repository must be 100% hermetic:
- **No Outbound Network Calls**: Tests must never initiate live HTTP requests, WebSocket connections, or external socket calls to third-party services (FMP, Massive/Polygon, FRED, Alpaca, Supabase, LLM provider APIs, or Gmail IMAP).
- **Socket & DNS Enforcement**: `apps/engine/tests/conftest.py` installs a global, session-scoped network guard fixture (`block_external_network_calls`). Any attempt to resolve external DNS or open a non-loopback TCP connection immediately raises a `RuntimeError`, failing the test fast before network packets leave the machine.
- **Proxy Environment Stripping**: the same `conftest.py` pops `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` and their lowercase variants from `os.environ` at import time. `httpx`, `requests`, and `supabase-py` honour those variables by default, so an ambient proxy configuration would otherwise route a supposedly-blocked request through a loopback proxy and slip past the socket guard.
- **Credential Independence**: Tests must never rely on ambient environment variables (`FMP_API_KEY`, `OPENAI_API_KEY`, etc.). When testing functions that check API keys, tests must explicitly mock or patch the key (e.g. `patch("tools.congress_tools.FMP_API_KEY", "test-key")`), ensuring tests pass reliably in clean CI runners.

## Zero Artificial Sleep & Test Latency Policy (MANDATORY)

Test suites must execute cleanly without artificial delays. Slow tests cannot be solved simply by adding parallel compute processes (`pytest -n auto`) if individual tests block on real-time sleeps, rate limiters, or retry backoffs.

- **Zero Unmocked Tenacity Retries**: Tenacity `@retry` decorators must specify exception filters (`retry_if_exception`) to fast-fail non-transient errors (such as `RuntimeError` from the hermetic socket guard or 401/403 HTTP errors) rather than retrying with exponential backoff (e.g. 4s + 4s + 8s). Tests asserting retry behavior must patch retry sleep (`patch.object(func.retry, "sleep", return_value=None)`).
- **Autouse Rate Limiter & Embedding Fixtures**: Global singletons (like `_MASSIVE_LIMITER` in `apps/engine/execution/market_data.py`) must be neutralized in `apps/engine/tests/conftest.py` via autouse fixtures (`hermetic_massive_rate_limiter`, `hermetic_memory_store_embeddings`) so tests never wait for token bucket replenishment.
- **Environment-Aware Fallback Delays**: Any loop or fallback logic that sleeps on transient connection failure (e.g. local autoresearch server checks) must detect `os.getenv("PYTEST_CURRENT_TEST")` and set delay to 0.0 seconds.
- **Latency Regression Suite**: `apps/engine/tests/test_test_suite_latency_guards.py` validates that rate-limited, retried, and fallback code paths execute in under 100ms.

See [[concepts/test-latency-guards]] for the detailed architectural breakdown.

## Related

- [[concepts/test-latency-guards]]
- [[concepts/project-linting]] — pre-commit hook scoping and CI workflow
- [[entities/verify-skill]] — the local full-suite runner and its 4-worker cap
- [[sources/engine-testing-source]]
- [[sources/web-testing-source]]
