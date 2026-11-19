---
tags: [testing, performance, latency, tenacity, rate-limiter, quality]
category: concept
---

# Test Latency Guards & Zero Artificial Sleep Policy

The Zero Artificial Sleep Policy is an architectural mandate ensuring that the test suite executes hermetically and instantaneously. Adding parallel processes (`pytest -n auto`) cannot solve test suite slowdowns when individual tests block synchronously on real-time sleeps, token-bucket rate limiters, or exponential retry backoffs.

## The Compute Scaling Illusion

When a test suite scales past 1,800 tests, developers often observe steep increases in wall-clock execution time (e.g. expanding from 25 seconds to several minutes). Attempting to resolve this by allocating more CPU cores or increasing `pytest-xdist` concurrency yields diminishing returns or outright stalls when worker processes block on real-time `time.sleep` or `asyncio.sleep` calls.

A single test that sleeps for 15 seconds costs 15 worker-seconds regardless of core availability. If several dozen tests encounter real-time sleep loops, entire worker queues stall, serialization bottlenecks emerge, and CI/CD pipelines slow down.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THE THREE LATENCY TRAPS                         │
├────────────────────────────────┬───────────────────────────────────────┤
│ Trap                           │ Cause & Penalty                       │
├────────────────────────────────┼───────────────────────────────────────┤
│ 1. Tenacity Retry Blindspot    │ `@retry` catches fatal socket guard   │
│                                │ `RuntimeError` and backs off 4s+4s+8s │
│                                │ -> 16s penalty per test               │
├────────────────────────────────┼───────────────────────────────────────┤
│ 2. Singleton Rate Limiter      │ Global `AsyncTokenBucketLimiter`      │
│                                │ drains tokens across parallel tests   │
│                                │ -> 12s sleep per call                 │
├────────────────────────────────┼───────────────────────────────────────┤
│ 3. Unmocked Fallback Loops     │ Server drops (Strata/Laya) sleep      │
│                                │ across multiple retry cycles          │
│                                │ -> 15s to 45s penalty                 │
└────────────────────────────────┴───────────────────────────────────────┘
```

## The Three Latency Traps

### 1. Unfiltered Tenacity Retries
When library or network calls are wrapped with Tenacity's `@retry(wait=wait_random_exponential(...), stop=stop_after_attempt(5))` without explicit `retry_if_exception` filters, Tenacity catches *every* exception.

In hermetic test environments, `apps/engine/tests/conftest.py` installs a global socket guard (`block_external_network_calls`) that immediately raises a `RuntimeError` whenever an external network connection is attempted. When Tenacity catches this `RuntimeError`, it treats it as a transient network glitch and sleeps for exponential backoff intervals (e.g. 4s, 4s, 8s). A single test hitting an unmocked embedding or client factory thus incurs a 16-second penalty before re-raising the error.

### 2. Global Singleton Rate Limiters
Production code often enforces rate limits using global singleton token buckets (such as `_MASSIVE_LIMITER = AsyncTokenBucketLimiter(5.0, 60.0)` in `apps/engine/execution/market_data.py`).

While individual unit tests mock downstream HTTP requests, they frequently call the public wrapper function without mocking the rate limiter itself. After 5 mock calls consume the bucket's burst capacity, subsequent tests block on `await limiter.acquire()`, sleeping for 12 seconds per token while waiting for the global bucket to replenish.

### 3. Fallback and Health-Check Loops
Pipelines that communicate with local AI servers (such as Strata or Laya in `apps/engine/local_autoresearch/document_builder.py`) or external quote providers feature fallback loops with sleep delays (e.g., 3 attempts with 5-second delays). In unit tests where the target service is intentionally offline or mocked via high-level stubs, inner helper functions execute real sleep cycles (3 × 15s = 45 seconds).

## The Four-Layer Prevention Protocol

To guarantee sub-second execution across all tests, the codebase implements four complementary latency guards:

### Layer 1: Tenacity Exception Filtering (`retry_if_exception`)
All Tenacity retry decorators must declare an explicit filter that separates transient server errors (HTTP 502, 503, 504, 429) from fatal programming and configuration errors.

Non-retryable exceptions that must fail fast without backoff:
- `RuntimeError` (raised by test socket and DNS guards)
- Client errors: HTTP 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)
- Validation errors: `pydantic.ValidationError`, `KeyError`, `TypeError`, `ValueError`

Example pattern from `apps/engine/memory/embeddings.py`:
```python
def _is_retryable_embedding_error(exc: BaseException) -> bool:
    if isinstance(exc, RuntimeError):
        return False
    status_code = getattr(exc, "status_code", None)
    if status_code in (400, 401, 402, 403, 404):
        return False
    return True

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception(_is_retryable_embedding_error),
)
def _call_embed_with_retry(...):
    ...
```

#### Exception-Chain Walking
`_is_retryable_embedding_error` in `apps/engine/memory/embeddings.py` does not inspect only the top-level exception. It walks the full `__cause__` / `__context__` chain and fails fast if **any** link is a `RuntimeError`, `ValueError`, `TypeError`, `KeyError`, carries a `code`/`status_code` of 400/401/402/403/404, or whose message matches `blocked during test`, `unauthorized`, or `prepayment credits`. Tenant SDKs routinely wrap the real cause (a socket-guard `RuntimeError`, an auth error) inside a provider-specific exception, so checking only the outermost object let a wrapped guard escape the filter and pay the full backoff. It returns `True` only when every link in the chain looks transient.

### Layer 2: Fast-Forwarding Retry Delays in Unit Tests
Tests specifically designed to verify retry logic or resilience must never sleep in real time. They must patch the Tenacity retry sleep handler or use zero-delay configurations:

```python
with patch.object(_call_embed_with_retry.retry, "sleep", return_value=None):
    # Executes all retry attempts instantaneously without sleep latency
    result = _call_embed_with_retry(...)
```

The same rule applies to plain `asyncio.sleep` calls inside a retried production path. `apps/engine/core/llm/verification.py` exposes its sleep through a module-level `asyncio_sleep` symbol so verification tests can patch `core.llm.verification.asyncio_sleep` instead of waiting out the retry interval; `apps/engine/tests/test_verification.py` installs that patch in every test that reaches `verify_trading_decision`.

### Layer 3: Autouse Global Conftest Fixtures
Global singleton rate limiters and external embedding lookups must be neutralized in `apps/engine/tests/conftest.py` via autouse fixtures:

- `hermetic_memory_store_embeddings`: Mocks `memory.store.get_embedding` to return dummy vector representations (`[0.1] * 768`), `memory.store.get_embeddings_batch` to return `[[0.1] * 768]`, and `analysis.consensus.get_embedding` to the same dummy vector. Tests can override this fixture locally when specifically asserting embedding dimensions. The consensus patch is required because the consensus engine imports the embedding helper directly; without it, consensus clustering tests reach the live Gemini embedding client.
- `hermetic_massive_rate_limiter`: Replaces `_MASSIVE_LIMITER.acquire` with `AsyncMock(return_value=None)` so mock test suites never wait for token bucket replenishment.

Feature-local autouse fixtures extend the same idea where a module has its own network boundaries. `apps/engine/tests/test_verification.py` patches `core.llm.verification.retrieve_for_decision` (RAG), `core.llm.verification.log_reasoning_trace` (Supabase), and `execution.market_data.MarketDataManager.get_quote` (FMP) for its whole module, so no verification test can fall through to a live provider.

### Layer 4: Test Environment Detection (`PYTEST_CURRENT_TEST`)
When fallback loops or backoff delays are embedded deep in execution or document generation paths, they must check for the active test runner and zero the delay:

```python
retry_delay_seconds = 5.0
if os.getenv("PYTEST_CURRENT_TEST") and retry_delay_seconds >= 1.0:
    retry_delay_seconds = 0.0
```

The same guard is applied to the production call throttles that would otherwise serialize every mocked request:

- **FMP provider throttling (`apps/engine/execution/providers/fmp.py`)** — the `FINANCIAL_API_THROTTLE_SECONDS` pre-call wait, the `2 ** (attempt - 1)` exponential backoff between quote/history retries, the fixed `asyncio.sleep(FINANCIAL_API_THROTTLE_SECONDS)` before the aftermarket path, and the 1-second aftermarket retry delay are all skipped when `PYTEST_CURRENT_TEST` is set. The retry *count* and error semantics are unchanged; only the wall-clock waits are suppressed, so a mocked test exercises every attempt instantly.
- **Embedding inter-call pacing (`apps/engine/memory/embeddings.py`)** — the `_EMBED_MIN_INTERVAL` gap enforced between `get_embeddings_batch` calls is skipped under pytest. `_last_embed_time` is still updated so production pacing semantics are untouched.

## Latency Guard Regression Suite

The engine includes a dedicated regression suite in `apps/engine/tests/test_test_suite_latency_guards.py`. It runs latency benchmarks against all retry, rate-limiting, and fallback codepaths, enforcing that:
1. `_is_retryable_embedding_error` fast-fails `RuntimeError` and auth errors under 100ms, including when they are wrapped in a provider exception's `__cause__`/`__context__` chain.
2. `hermetic_massive_rate_limiter` permits 10 rapid calls to `_fetch_with_backoff` in under 100ms without rate-limiter stalls.
3. `generate_daily_document` completes fallback attempts in under 100ms without waiting for real-time sleeps.

## Related

- [[concepts/test-coverage]] — Pre-commit ratchet thresholds and hermetic testing mandates
- [[sources/engine-testing-source]] — Engine testing patterns, DI conventions, and boundary mocking
- [[entities/engine]] — Engine service architecture and execution pipeline
- [apps/engine/tests/conftest.py](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tests/conftest.py) — Global network guards and autouse latency fixtures
- [apps/engine/tests/test_test_suite_latency_guards.py](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tests/test_test_suite_latency_guards.py) — Latency guard verification tests
