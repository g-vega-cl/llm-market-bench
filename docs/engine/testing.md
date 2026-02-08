# Testing Strategy & Execution

This document outlines the testing infrastructure for the `llm-market-bench` engine, ensuring code quality, resilience, and a warning-free developer experience.

## Quick Start

### Global (Root)
To run the full suite from the repository root using the project virtual environment:
```bash
./apps/engine/venv/bin/python3 -m pytest
```

### Engine (App)
To run tests while working specifically in the engine directory:
```bash
./venv/bin/python3 -m pytest
```

To run with verbose output:

```bash
python3 -m pytest -v
```

## Test Suites

The engine tests are located in `apps/engine/tests/` and cover the following areas:

### 1. Analysis & LLM

| Test File | Coverage |
|-----------|----------|
| `test_analysis_logic.py` | Schema validation, `analyze_chunks` orchestration, batch processing |
| `test_batch_analysis.py` | Validates all chunks are analyzed in a single LLM call per provider |
| `test_llm_tools.py` | Tool calling interface for `get_stock_quote` across providers |
| `test_call_counts.py` | Verifies API call efficiency and batching |

### 2. Consensus & Memory

| Test File | Coverage |
|-----------|----------|
| `test_consensus.py` | Semantic grouping, weighted voting, event promotion |
| `test_consolidation.py` | `process_decision_consensus` function: decision grouping by ticker/signal, synthesis of unified reasonings |
| `test_memory_chains.py` | Parent-child relationships, auto-resolution of events |
| `test_memory_optimization.py` | RESOLVED status filtering, relevance decay |
| `test_memory_rag.py` | Vector similarity search, context retrieval |
| `test_momentum.py` | Trend velocity calculation, concept merging, decay |

### 3. Execution & Portfolio

| Test File | Coverage |
|-----------|----------|
| `test_portfolio.py` | Portfolio initialization, position management, trade execution |
| `test_reg_t_validation.py` | Buying power calculation, SMA floor enforcement |
| `test_sell_guardrails.py` | Portfolio ownership validation for SELL signals |
| `test_performance_snapshot.py` | Daily equity curve recording, idempotency |
| `test_atomic_fix.py` | "Commit at the End" atomic settlement pattern |

### 4. Validation & Market Data

| Test File | Coverage |
|-----------|----------|
| `test_validation.py` | Existence, price banding, and liquidity guardrails |
| `test_market_data.py` | Cache-first architecture, TTL expiration, fallback logic |
| `test_yfinance_provider.py` | yfinance provider integration and error handling |

### 5. Attribution & Pipeline

| Test File | Coverage |
|-----------|----------|
| `test_attribution.py` | Decision persistence, UPSERT idempotency, trade linking |
| `test_main_flow.py` | End-to-end pipeline orchestration |

### 6. Resilience & Core

| Test File | Coverage |
|-----------|----------|
| `test_resilience.py` | Individual LLM failures, graceful degradation |
| `test_newsletter.py` | Text cleaning, source ID generation, chunk hashing |
| `test_config.py` | Environment variable loading and validation |
| `test_client_cleanup.py` | LLM client resource cleanup |
| `test_fix_verification.py` | Regression tests for specific bug fixes |

### 7. Verification Scripts

These are manual verification scripts for specific features:

| Script | Purpose |
|--------|---------|
| `verify_step_15.py` | Verifies reasoning is correctly embedded into long-term memory |
| `verify_portfolio_upsert.py` | Verifies portfolio position upsert logic |

## Warning-Free Policy

We maintain a strict **Zero Warning** policy for the test suite. To achieve this, we have implemented:

- **SDK Migration**: Migrated from the deprecated `google-generativeai` to the modern `google-genai` package to eliminate `FutureWarning` noise.
- **Transitive Dependency Fixes**: Pinned `pydantic<2.12.0` to resolve deprecation warnings triggered by third-party libraries (like `pyiceberg`).
- **Signature Synchronization**: All core analysis tests (`test_analysis_logic.py`, `test_batch_analysis.py`, etc.) are synchronized with the 3-tuple return signature of `analyze_chunks` to ensure pipeline stability.

## Best Practices

### Mocking External Dependencies

To ensure tests run reliably in CI/CD environments without requiring API keys or external service access:

**Gemini Embeddings**: Use `@pytest.fixture(autouse=True)` to mock `get_embedding` in attribution tests:
```python
@pytest.fixture(autouse=True)
def mock_get_embedding():
    """Mock get_embedding to avoid API calls."""
    with patch("attribution.service.get_embedding") as mock:
        mock.return_value = [0.1] * 768
        yield mock
```

**Async Functions**: When mocking async functions like `ingest_newsletters`, use `AsyncMock` to ensure compatibility:
```python
from unittest.mock import AsyncMock
monkeypatch.setattr("main.ingest_newsletters", AsyncMock(return_value=[]))
```

**Async Tests**: Mark tests that call async functions with `@pytest.mark.asyncio` and use `await`:
```python
@pytest.mark.asyncio
async def test_ingest_newsletters_summary(caplog):
    await ingest_newsletters(newer_than_days=1)
```

## CI/CD Integration

Tests are automatically executed on every Push and Pull Request via GitHub Actions. A failure in any test prevents merging to the main branch.

---
*Last Updated: January 2026*
