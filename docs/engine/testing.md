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
|-----------|---------|
| `test_analysis_logic.py` | Schema validation, `analyze_chunks` orchestration, batch processing |
| `test_batch_analysis.py` | Validates all chunks are analyzed in a single LLM call per provider |
| `test_discovery_agent.py` | Unit tests for DiscoveryAgent single-call JSON parsing, max 5 asset limiting, and validation |
| `test_discovery_quality.py` | Integration tests for DiscoveryService and agent delegation |
| `test_llm_tools.py` | Tool calling interface for `get_stock_quote`, `calculate_buy/sell_quantity` across providers |
| `test_call_counts.py` | Verifies API call efficiency and batching |
| `test_post_analysis.py` | Post-analysis model validation, existing memory skipping, price change calculation |

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
| `test_validation.py` | Existence and liquidity guardrails (price deviation removed per Approach 3) |
| `test_pre_injected_prices.py` | Pre-fetch market data extraction, prompt rewrites, staleness check, DecisionObject field changes |
| `test_market_data.py` | Cache-first architecture, TTL expiration, last-known-price backfill |
| `test_yfinance_provider.py` | yfinance provider integration and error handling |

### 5. Attribution & Pipeline

| Test File | Coverage |
|-----------|----------|
| `test_attribution.py` | Decision persistence, UPSERT idempotency, trade linking, empty upsert response raises error |
| `test_main_flow.py` | End-to-end pipeline orchestration, pre-save guard aborts trade on missing decision_id |

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
| `simulate_uncrowded_trade.py` | Simulates an "uncrowded trade" scenario to evaluate the pipeline and verification logic |

## Warning-Free Policy

We maintain a strict **Zero Warning** policy for the test suite. To achieve this, we have implemented:

- **SDK Migration**: Migrated from the deprecated `google-generativeai` to the modern `google-genai` package to eliminate `FutureWarning` noise.
- **Transitive Dependency Fixes**: Pinned dependency versions (see `requirements.txt`) to resolve deprecation warnings triggered by third-party libraries.
- **Signature Synchronization**: All core analysis tests (`test_analysis_logic.py`, `test_batch_analysis.py`, etc.) are synchronized with the 3-tuple return signature of `analyze_chunks` to ensure pipeline stability.

## Best Practices

### Mocking External Dependencies

To ensure tests run reliably in CI/CD environments without requiring API keys or external service access:

**Global Dummy Environment Variables**: We use a session-scoped `autouse` fixture in `conftest.py` to set dummy values for required environment variables (like `SUPABASE_PROJECT_URL`). This prevents `ValueError` when components like `get_supabase_client()` are initialized during test collection or execution in environments without a `.env` file.

```python
# In apps/engine/tests/conftest.py
if not os.getenv("SUPABASE_PROJECT_URL"):
    os.environ["SUPABASE_PROJECT_URL"] = "https://mock.supabase.co"
if not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock-key"
```

**fully_mocked_main Fixture**: For integration tests of the `main.py` pipeline, use the `fully_mocked_main` fixture. It provides a comprehensive set of mocks for all external services (DB, Market Data, LLMs) in a single, reusable setup.

```python
def test_main_ingestion_guardrail(fully_mocked_main, monkeypatch):
    """Test that main.py stops if no newsletters are returned."""
    from main import main
    md = fully_mocked_main
    md["ingest"].return_value = [] # Mock empty ingestion
    # ...
    main()
```

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

**MarketDataManager & is_market_open**: When mocking `MarketDataManager`, you MUST provide an `AsyncMock` for `is_market_open`. Failure to do so will result in `TypeError: object MagicMock can't be used in 'await' expression`.
```python
with patch("execution.validation.MarketDataManager") as mock_manager_cls:
    mock_manager = mock_manager_cls.return_value
    mock_manager.is_market_open = AsyncMock(return_value=True)
    mock_manager.get_quote = AsyncMock(return_value=mock_data)
```

**Supabase Initialization in Tests**: `MarketDataManager.__init__` calls `get_supabase_client()`, which requires environment variables. To avoid `ValueError` in CI environments, always mock `MarketDataManager` at the class level or mock `core.db.get_supabase_client`. Note that if a module uses a local import (e.g., `from execution.market_data import MarketDataManager` inside a function), you must patch the source: `patch("execution.market_data.MarketDataManager")`.

**Multi-Block LLM Responses**: When testing analysis or verification loops that use `response_model=List[Model]` (to handle multiple tool call blocks), mocks should return a list of objects (e.g., `[mock_result]`). However, the production logic is resilient to single object returns via the `ensure_list` utility.

### Async Tests: Mark tests that call async functions with `@pytest.mark.asyncio` and use `await`:
```python
@pytest.mark.asyncio
async def test_ingest_newsletters_summary(caplog):
    await ingest_newsletters(newer_than_days=1)
```

### Unit Testing LLM Handlers: Mock at the Boundary

When testing LLM handler methods (like `gemini.run_tool_loop`), create pure unit tests by:

1. **Mock the raw client's `aio.models.generate_content` method directly**, not the SDK internals
2. **Inspect the `config` argument** passed to the mock to verify correct configuration
3. **Do NOT rely on HTTP request interception** or SDK serialization internals
4. **Never use real API keys** — the mock provides all needed responses

**❌ Bad Pattern** (brittle, tests SDK internals, relies on serialization):
```python
# DO NOT: Creates real client, patches internal _async_request, inspects serialized HTTP body
client = genai.Client(api_key="x")
api = client._api_client
api._async_request = fake_request
await client.aio.models.generate_content(...)
request_data = captured["kwargs"]["http_request"].data
assert "automaticFunctionCalling" in request_data  # Tests SDK serialization!
```

**✅ Good Pattern** (isolated, fast, tests your logic only):
```python
@pytest.mark.asyncio
async def test_gemini_afc_configuration():
    from unittest.mock import AsyncMock, MagicMock
    from core.llm.handlers import gemini

    raw_client = MagicMock()
    mock_aio = raw_client.aio
    mock_aio.models.generate_content = AsyncMock(
        return_value=MagicMock(candidates=[MagicMock(content=None)])
    )

    messages = [{"role": "user", "content": "hi"}]
    await gemini.run_tool_loop(
        raw_client=raw_client,
        model_name="gemini-1.5-flash",
        messages=messages,
        override_tools=[{"name": "foo", "parameters": {}}],
        enable_google_search=True,
    )

    # Verify the config object itself — no serialization involved
    config = mock_aio.models.generate_content.call_args.kwargs['config']
    assert config.automatic_function_calling is not None
    assert config.automatic_function_calling.disable is True
```

**Why the good pattern is better:**
- Tests **your code's behavior** (setting config fields) not SDK internals
- Immune to SDK version changes (serialization details may vary)
- Faster (no HTTP layer, no pydantic model serialization)
- No need for valid API keys
- Clear intent: "when google_search=True, handler should set `config.automatic_function_calling.disable = True`"

### Dependency Injection for Analysis Functions

Analysis functions like `run_contrarian_analysis` accept dependencies via parameters rather than creating them internally. This enables clean unit testing without patching internal imports.

**Pattern (contrarian.py example)**:
```python
async def run_contrarian_analysis(
    chunks: List[dict],
    other_decisions: List[DecisionObject],
    context: str = "",
    portfolio: Portfolio = None,
    market_data: MarketDataManager = None,
    llm_client = None,
    retrieve_context_fn: Callable = None
) -> Tuple[List[DecisionObject], List[MacroEvent]]:
    # Use provided dependencies, or create defaults
    if portfolio is None:
        portfolio = Portfolio(owner_id="contrarian_agent")
    # ...
```

**Testing with DI**:
```python
@pytest.mark.asyncio
async def test_contrarian_with_di(self):
    """Test using dependency injection - no internal import patching needed."""
    mock_portfolio = MagicMock()
    mock_portfolio.positions = {}
    mock_portfolio.initialize = AsyncMock(return_value=None)
    mock_portfolio.calculate_reg_t_metrics = MagicMock()
    mock_portfolio.save_metrics = AsyncMock(return_value=None)
    mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000")

    mock_market_data = MagicMock()
    mock_market_data.get_quote = AsyncMock(return_value=None)

    mock_gemini_client = MagicMock()
    mock_response = MagicMock()
    mock_response.decisions = []
    mock_response.macro_events = []
    mock_gemini_client.chat.completions.create = AsyncMock(return_value=[mock_response])

    mock_retrieve_context = MagicMock(return_value=[])

    from analysis.contrarian import run_contrarian_analysis
    
    result_decisions, result_events = await run_contrarian_analysis(
        [{"source_id": "src_1", "content": "test"}],
        [DecisionObject(signal="BUY", confidence=80, reasoning="Test", ticker="AAPL", source_id="src_1")],
        context="test context",
        portfolio=mock_portfolio,
        market_data=mock_market_data,
        llm_client=mock_gemini_client,
        retrieve_context_fn=mock_retrieve_context
    )

    assert isinstance(result_decisions, list)
    assert isinstance(result_events, list)
```

**Why DI over patching internal imports?**
- **Explicit dependencies**: Tests clearly show what the function needs
- **No import ordering issues**: No need to patch before module import
- **No fragile patch paths**: No `patch("analysis.contrarian.X")` required
- **Follows SOLID principles**: Single responsibility, dependency inversion

### Market Hours & Determinism
The `run_ingest` function in `main.py` contains a mandatory check for US Market Hours (09:30–16:00 ET). To ensure tests are deterministic and can run at any time (e.g., during overnight CI/CD runs), always pass `force=True` when calling `run_ingest` in test cases:

```python
# Correct pattern for pipeline tests
await run_ingest(force=True)
```

## CI/CD Integration

Tests are automatically executed on every Push and Pull Request via GitHub Actions. A failure in any test prevents merging to the main branch.

## Reasoning Trace Audit

The `llm_reasoning_logs` table captures every LLM interaction — system prompts, intermediate tool calls, tool results, and thought traces (for Gemini/DeepSeek). The frontend provides a research dashboard at `/reasoning` with categorized trace browsing, tabbed JSON inspection, and one-click raw export.

Key columns: `task_type` (INGESTION, VERIFICATION, CONSENSUS), `model_name`, `prompt` (JSONB message array), `response` (JSONB), `metadata` (JSONB with tickers and source IDs).

**Data Isolation**: Before passing messages to instructor for structured extraction, the engine deep-copies the message history (`copy.deepcopy(messages)`). This prevents instructor's schema injection from polluting the audit logs with Pydantic JSON bloat.
