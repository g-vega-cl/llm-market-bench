---
tags: [tooling, resilience, error-handling, tool-audit]
category: concept
---

# Defensive Tool Dispatch

Resilience layer in `core/llm/handlers/base.py` that wraps every LLM tool call. LLMs occasionally emit malformed tool arguments — using a `symbol` key instead of `ticker`, omitting a required argument, or invoking a tool whose provider raises unexpectedly. Defensive dispatch ensures these mistakes produce clean, model-readable errors and a full audit record instead of crashing an entire analysis batch.

## Mechanisms

- **Argument resolution**: `_get_ticker()` accepts either `ticker` or `symbol`, strips and upper-cases the value. Optional arguments use `args.get(...)` with sane defaults (e.g. `percentage` default 20 for buys / 100 for sells, `period="polymarket"` for prediction markets, `SPY` for vol surface).
- **Ticker validation**: Invalid tickers are rejected with a format guidance message before dispatch.
- **Required-argument guard**: A `ticker_required_tools` set enumerates every tool that needs a ticker; missing tickers return `Error: Missing required 'ticker' argument for <tool>.` instead of raising `KeyError`.
- **Error boundary**: `execute_tool` wraps `_dispatch_tool` in a try/except, logging the exception (`logger.exception`) and returning `Error executing <tool>: <exc>` while recording `status="error"` in the audit log.
- **Universal timing audit**: Every call measures wall-clock `duration_ms`; calls at or above 5000 ms emit a `[tool_audit] Slow tool:` warning, all other completions log at info level, and each execution is non-blockingly persisted via `async_record_tool_audit` to `public.tool_execution_logs`.

## Related

- [[entities/tool-audit]]
- [[concepts/tool-enforcement]]
- [[concepts/auditability]]
- [[entities/tool-registry]]
