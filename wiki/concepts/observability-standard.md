---
tags: [logging, debugging, audit, observability]
category: concept
---

# Observability Standard (May 2026 Audit)

## Philosophy
The platform prioritizes **traceability over brevity**. Since the engine runs autonomously and its logs are consumed by an automated LLM-based audit system (DeepSeek), every failure must provide enough context for root-cause analysis without manual intervention.

## Core Mandates

### 1. Traceback Hardening
Always use `logger.exception()` in `except` blocks for unexpected failures. This automatically attaches the full stack trace to the log message.
- **BAD**: `logger.error(f"Failed to fetch {ticker}: {e}")`
- **GOOD**: `logger.exception(f"Failed to fetch {ticker}")`

### 2. Module Identification
Loggers must be named by module to distinguish between engine logic and library logs (e.g., `ib_async`, `httpx`).
```python
logger = logging.getLogger("engine.execution.fmp")
```

### 3. Granular Pipeline Tracking
The pipeline must log its progress using success/total ratios. This allows monitoring systems to detect partial failures that don't crash the entire process.
- **Example**: `Successfully saved 18/20 snapshots to Supabase.`

### 4. Audit-Ready Logs & System Audits
Logs captured during the pipeline run (e.g., in `main.py`) are saved to the `ingestion_logs` table in Supabase. These logs are then analyzed by the `audit` command (`apps/engine/core/audit/runner.py`), which uses an LLM to identify anomalies and runs standard SQL integrity checks defined in `apps/engine/core/audit/checks.py`.

#### System Audit Valid Decision Statuses
Decision status checks (`invalid_decision_status`) enforce a strict set of valid decision statuses to flag data corruption:
- `CREATED`, `EXECUTED`, `VALIDATED`
- Rejection statuses: `REJECTED_MARGIN`, `REJECTED_OWNERSHIP`, `REJECTED_REDUNDANCY`, `REJECTED_TOOL_USAGE`, `REJECTED_VERIFICATION`, `REJECTED_HALLUCINATION`, `REJECTED_PRICE_DEVIATION`, `REJECTED_LIQUIDITY`, `REJECTED_MARKET_CLOSED`, `REJECTED_LIMIT_PRICE`, `REJECTED_STALE_QUOTE`
- Provider error: `ERROR_PROVIDER`

### 5. Enriched Diagnostic Context on Rejection
When the engine rejects a model's trading recommendation due to a safety guardrail (e.g., failing Hard Tool Enforcement checks), the log warning must include immediate diagnostic context to enable root-cause analysis:
- The log must report the **total message count** in the history.
- The log must report **all actual tool calls** detected in the message history, enabling developers and automated audit systems to immediately see what tools were called instead.
- **Example**: `HARD ENFORCEMENT: Agent recommended BUY for AAPL without executing 'calculate_buy_quantity' tool. Total messages in history: 5. Tools called: ['get_stock_quote({"ticker": "AAPL"})']. Rejecting trade.`

## Reasoning Trace Serialization Safety

`log_reasoning_trace` in `apps/engine/core/llm/logger.py` persists every LLM prompt and response to the reasoning archive, so the payload must be JSON-serializable before it reaches Supabase. Its `sterilize_data(obj, depth=0)` helper recursively converts arbitrary objects into plain JSON primitives, and three guards keep the serialization itself from becoming a failure mode:

1. **Bounded recursion depth** — recursion stops at `depth > 12` and the remaining subtree is stringified. Provider SDKs, ORM rows, and client handles routinely form back-references (`obj.parent.children[i].parent …`), which previously raised `RecursionError` and lost the entire trace. A trace that is partially stringified is still an audit record; a trace that raised is not.
2. **Mock short-circuit** — objects whose `type(obj).__module__` starts with `unittest.mock` are stringified immediately rather than walked via `__dict__`. `MagicMock` fabricates a new child mock on every attribute access, so `hasattr(obj, "model_dump")` / `hasattr(obj, "__dict__")` walking amplified into unbounded trees during tests.
3. **Deterministic primitive ordering** — primitives (`str`, `int`, `float`, `bool`, `None`) are returned first, then `dict`, then `list`, then objects exposing `model_dump()` (Pydantic v2) or `dict()` (Pydantic v1), then any object with a public `__dict__`, and only then `str(obj)` as the terminal fallback. Private (`_`-prefixed) attributes are dropped from `__dict__` walks.

## Implementation Details

### Python (Engine)
- Configuration: `apps/engine/core/config.py`
- Main capturing logic: `apps/engine/main.py` using `io.StringIO` and a `StreamHandler`.

### TypeScript (Web)
- Query Cache Errors: Logged globally in `apps/web/src/lib/query-client.tsx`.
- Mutation Errors: Logged globally to ensure UI-driven actions are traceable in the browser console/Sentry.
- Canonical Web Error Tracking: Client-side exceptions and service disruptions are reported to PostHog Error Tracking via `posthog.captureException(err, properties)` (emitting native `$exception` events), with automated security scanner noise suppressed via `before_send`, as detailed in [[concepts/posthog-stealth-proxy]].

## Related
- [[entities/pipeline]]
- [[entities/auto-wiki]]
- [[sources/anomaly-detector-source]]
- [[concepts/agent-workflow]]
- [[concepts/posthog-stealth-proxy]]
- [[concepts/reasoning]]
