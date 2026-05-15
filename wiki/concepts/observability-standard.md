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

### 4. Audit-Ready Logs
Logs captured during the pipeline run (e.g., in `main.py`) are saved to the `ingestion_logs` table in Supabase. These logs are then analyzed by the `audit` command, which uses an LLM to identify anomalies.

## Implementation Details

### Python (Engine)
- Configuration: `apps/engine/core/config.py`
- Main capturing logic: `apps/engine/main.py` using `io.StringIO` and a `StreamHandler`.

### TypeScript (Web)
- Query Cache Errors: Logged globally in `apps/web/src/lib/query-client.tsx`.
- Mutation Errors: Logged globally to ensure UI-driven actions are traceable in the browser console/Sentry.

## Related
- [[entities/pipeline]]
- [[entities/auto-wiki]]
- [[sources/anomaly-detector-source]]
