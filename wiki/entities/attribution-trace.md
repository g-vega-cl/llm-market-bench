---
tags: [attribution, trace, tool-calls, auditability]
category: entity
---

# Attribution Trace

Extracts and normalizes tool-call traces from LLM responses across OpenAI and Anthropic formats, enabling end-to-end auditability of every decision's reasoning and tool execution history.

## Overview

The Attribution Trace module lives in `apps/engine/attribution/` and provides deterministic extraction of tool calls from raw LLM output. It supports both OpenAI-style `tool_calls` arrays and Anthropic-style content block lists with `type='tool_use'`, normalizing them into a unified trace structure.

## Key Capabilities

- **OpenAI format parsing** — reads `tool_calls` arrays, extracting function name and arguments.
- **Anthropic format parsing** — reads content block lists, extracting `tool_use` blocks.
- **Empty-trace handling** — returns an empty list when no tool calls were made.
- **Metadata propagation** — preserves `metadata` alongside `reasoning` when enriching trade records.

## Integration

Used by the engine's analysis pipeline to attach execution traces to decisions. The trace is stored under `decisions.metadata->'execution_trace'` and surfaced in the web UI via `ExecutionTraceView`.

## Related

- [[concepts/execution]]
- [[entities/engine]]
- [[concepts/rag-strategy]]
