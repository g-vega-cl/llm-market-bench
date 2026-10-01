---
tags: [llm, analysis, pipeline, engine, refactoring]
category: entity
---

# Analysis Pipeline

The `core/llm/analysis_pipeline/` package is a vertical-slice decomposition of the
LLM analysis flow. It holds the prompt-assembly, response-parsing, and validation
responsibilities that were formerly inlined in `core/llm/analysis.py`, leaving that
file as a thin orchestrator (`analyze_with_provider`) under the 300-LOC ceiling.

This follows the [[concepts/vertical-slice-islands]] pattern: each module owns one
domain concern end-to-end so that changes touch a single file instead of a
monolithic patch surface.

## Modules

| Module | Responsibility |
| :--- | :--- |
| `prompt_assembly.py` | News formatting, held-ticker / `$SYMB` extraction, experiment-tool resolution, web-search flags, provider message shaping, schema hints, extraction args, message orchestration |
| `response_parsing.py` | JSON repair, multi-strategy parsing, fallback model creation, Instructor extraction with retry, multi-block aggregation |
| `validation.py` | History tool scanning, hard tool enforcement, portfolio ownership validation, attribution trace attachment |

## Orchestrator Flow

`analyze_with_provider` drives the pipeline in ordered stages:

1. **Resolve experiment tools** — `prompt_assembly.resolve_experiment_tools` loads
   the active autoresearch variant's `selected_tools` for experiment-owned models,
   force-injects `calculate_buy_quantity` / `calculate_sell_quantity`, and intercepts
   `web_search` into a native flag. `resolve_web_search_flag` falls back to per-provider
   config defaults (`ENABLE_*_WEB_SEARCH`) when no override exists.
2. **Assemble prompt** — `prompt_assembly.assemble_analysis_messages` builds the
   provider-specific analysis or macro messages (menu summaries take priority over raw
   chunk text).
3. **Run initial tool loop** — `_execute_provider_tool_loop` dispatches to provider
   handlers (`openai`, `deepseek`, `anthropic`, `gemini`, `minimax`) with the resolved
   tool set. A `safe_deepcopy` snapshot is preserved for verification.
4. **Final structured extraction** — messages are shaped with
   `prepare_messages_for_provider`, args built with `build_provider_extraction_args`,
   and `response_parsing.extract_structured_response` runs Instructor with up to 3
   attempts plus JSON-repair recovery on validation errors. Results are aggregated by
   `aggregate_response_blocks`.
5. **Retry on missing tools** — `validation.detect_missing_tool_decisions` finds BUY/SELL
   decisions lacking their mandatory quantity tool call; `build_tool_correction_message`
   injects a correction prompt and the tool loop is re-run once before re-extraction.
6. **Hard enforcement** — `validation.enforce_tool_call_history` overrides self-reported
   `buy_tool_called` / `sell_tool_called` flags based on actual history (see
   [[concepts/tool-enforcement]]).
7. **Portfolio ownership validation** — `validation.validate_portfolio_holdings`
   converts SELL signals for non-held tickers to HOLD, preserving the audit trail
   with a `REJECTED_OWNERSHIP` reasoning.
8. **Attribution trace** — `validation.attach_attribution_trace` binds an execution
   trace to the surviving decisions for factual logging.

## Backward Compatibility

`core/llm/analysis.py` re-exports the legacy private names (`_repair_json_string`,
`_try_parse_response`, `_scan_history_for_tools`, `_extract_held_tickers`, etc.) plus
`clients`, `PromptFactory`, and `log_reasoning_trace` so existing callers, tests, and
mock targets resolve unchanged.

## Related

- [[entities/engine]] — the data engine that owns this pipeline
- [[concepts/vertical-slice-islands]] — the decomposition pattern this package embodies
- [[concepts/tool-enforcement]] — the hard enforcement step in stage 6
- [[entities/tool-registry]] — where the canonical tool definitions come from
- [[concepts/rag-strategy]] — how targeted context reaches the analysis agents
