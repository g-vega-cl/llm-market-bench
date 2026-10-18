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

### Layer 2: Fast-Forwarding Retry Delays in Unit Tests
Tests specifically designed to verify retry logic or resilience must never sleep in real time. They must patch the Tenacity retry sleep handler or use zero-delay configurations:

```python
with patch.object(_call_embed_with_retry.retry, "sleep", return_value=None):
    # Executes all retry attempts instantaneously without sleep latency
    result = _call_embed_with_retry(...)
```

### Layer 3: Autouse Global Conftest Fixtures
Global singleton rate limiters and external embedding lookups must be neutralized in `apps/engine/tests/conftest.py` via autouse fixtures:

- `hermetic_memory_store_embeddings`: Mocks `memory.store.get_embedding` to return dummy vector representations (`[0.1] * 768`) and `memory.store.get_embeddings_batch` to return `[[0.1] * 768]`. Tests can override this fixture locally when specifically asserting embedding dimensions.
- `hermetic_massive_rate_limiter`: Replaces `_MASSIVE_LIMITER.acquire` with `AsyncMock(return_value=None)` so mock test suites never wait for token bucket replenishment.

### Layer 4: Test Environment Detection (`PYTEST_CURRENT_TEST`)
When fallback loops or backoff delays are embedded deep in execution or document generation paths, they must check for the active test runner and zero the delay:

```python
retry_delay_seconds = 5.0
if os.getenv("PYTEST_CURRENT_TEST") and retry_delay_seconds >= 1.0:
    retry_delay_seconds = 0.0
```

## Latency Guard Regression Suite

The engine includes a dedicated regression suite in `apps/engine/tests/test_test_suite_latency_guards.py`. It runs latency benchmarks against all retry, rate-limiting, and fallback codepaths, enforcing that:
1. `_is_retryable_embedding_error` fast-fails `RuntimeError` and auth errors under 100ms.
2. `hermetic_massive_rate_limiter` permits 10 rapid calls to `_fetch_with_backoff` in under 100ms without rate-limiter stalls.
3. `generate_daily_document` completes fallback attempts in under 100ms without waiting for real-time sleeps.

## Related

- [[concepts/test-coverage]] — Pre-commit ratchet thresholds and hermetic testing mandates
- [[sources/engine-testing-source]] — Engine testing patterns, DI conventions, and boundary mocking
- [[entities/engine]] — Engine service architecture and execution pipeline
- [apps/engine/tests/conftest.py](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tests/conftest.py) — Global network guards and autouse latency fixtures
- [apps/engine/tests/test_test_suite_latency_guards.py](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tests/test_test_suite_latency_guards.py) — Latency guard verification tests
