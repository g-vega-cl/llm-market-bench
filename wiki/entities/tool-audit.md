---
tags: [audit, logging, tool-execution, database]
category: entity
---

# Tool Audit Logging

Non-blocking background audit logging for LLM tool execution. Records every tool call's inputs, outputs, duration, and metadata to a separate analytical PostgreSQL archive database via PostgREST, with zero impact on Supabase storage quota.

## Architecture

- **Ingress & Schema**: Logs are POSTed to a `public.tool_execution_logs` table exposed by PostgREST on port 3001, accessible locally or via Cloudflare Tunnel (`https://benchify-archive-db.clvg.uk`).
- **Non-blocking execution**: The `async_record_tool_audit` helper schedules the HTTP POST as a background asyncio task with a done callback for error logging. The calling tool experiences zero added latency.
- **Payload safety**: Tool outputs >1 MB are truncated to `MAX_PAYLOAD_BYTES` (1,048,576) with a `truncated` flag and original size recorded in metadata.
- **Resilience**: Network failures, timeouts, or PostgREST rejections are logged at warning level and never propagate exceptions to the main pipeline.

## Key Functions

- `record_tool_audit(...)` — Async coroutine that constructs the JSON payload and sends it to `{archive_base}/tool_execution_logs`. Returns `True` on success.
- `async_record_tool_audit(...)` — Schedules `record_tool_audit` in the background without awaiting, using the running event loop. Safe to call from synchronous contexts (falls back to a warning log if no loop exists).
- `get_archive_db_url()` — Resolves the target PostgREST URL: explicit `ARCHIVE_DB_URL` env var > GitHub Actions remote tunnel > localhost:3001.

## Integration

Used in `core/llm/handlers/base.py` for the `get_volatility_metrics` tool (Phase 1). Plans to extend to valuation, screening, research, and daily predictor tools (Phases 2–4).

## Related

- [[concepts/hybrid-database-archival]] — The archive database infrastructure
- [[concepts/auditability]] — Overall traceability philosophy
- [[entities/engine]] — The engine that invokes tools
