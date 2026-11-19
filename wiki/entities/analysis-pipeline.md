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
| `prompt_assembly.py` | News formatting, held-ticker / `$SYMB` extraction, autoresearch track resolution (`resolve_track_id`), experiment-tool resolution (`resolve_experiment_tools`, `_build_override_tool_list`), web-search flags, provider message shaping, schema hints (`build_schema_hint`), extraction args, message orchestration |
| `response_parsing.py` | JSON repair, multi-strategy parsing, fallback model creation, Instructor extraction with retry, MiniMax OpenAI-endpoint extraction (`extract_with_minimax_openai` / `sanitize_minimax_content` / `_compact_minimax_user_content`), multi-block aggregation |
| `validation.py` | History tool scanning, hard tool enforcement, portfolio ownership validation, attribution trace attachment |

## Orchestrator Flow

`analyze_with_provider` drives the pipeline in ordered stages:

1. **Resolve experiment tools** — `prompt_assembly.resolve_experiment_tools` resolves the
   model's track through `prompt_assembly.resolve_track_id` (which scans
   `AUTORESEARCH_TRACKS` for the track whose owner list contains the model, honouring an
   explicit `track_id` override first) and also accepts membership in
   `AUTORESEARCH_EXPERIMENT_OWNER_IDS`. A model that appears only in `AUTORESEARCH_TRACKS`
   (e.g. `gpt-6-luna` under `track_openai`) therefore still receives its track's tool set.
   The active variant's `selected_tools` are mapped to canonical tool definitions by
   `_build_override_tool_list`, which force-injects `calculate_buy_quantity` /
   `calculate_sell_quantity`, logs a warning for unknown tool names, and intercepts
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
   `aggregate_response_blocks`. Two providers take a dedicated path (see
   [Provider-Specific Extraction Contracts](#provider-specific-extraction-contracts)):
   DeepSeek gets an appended JSON-only instruction turn, and MiniMax bypasses
   Instructor entirely for its OpenAI-compatible endpoint.
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

## Schema Hints (`build_schema_hint`)

`prompt_assembly.build_schema_hint(response_model)` produces the JSON shape embedded in
validation-recovery and extraction prompts. It inspects Pydantic v2 `model_fields`
(falling back to `hasattr` for non-Pydantic objects) to decide whether the response model
carries `decisions`, `macro_events`, or both, and emits a fully-populated item template
rather than an ellipsis stub:

- **Decision item** — `ticker`, `signal` (`BUY|SELL|HOLD`), `allocation_percentage`,
  `catalyst_type` (the full `MACRO|EARNINGS|M_A|PRODUCT|REGULATORY|EVENT|INNOVATION|TECHNICAL|UNCROWDED_TRADE|OTHER`
  enum), `catalyst_duration` (`INTRADAY|SHORT_TERM|MEDIUM_TERM|LONG_TERM`), `confidence`,
  `reasoning`, `source_id`.
- **Macro item** — `event_name`, `impact` (`BULLISH|BEARISH|NEUTRAL`), `catalyst_type`,
  `is_ongoing`, `is_future_catalyst`, `importance_score`, `confidence`, `reasoning`,
  `scenario_analysis`, `source_id`.

Because the check reads `model_fields`, a Pydantic v2 response class can never fall
through to the `"{}"` default — the previous `hasattr`-only check returned an empty
schema for classes whose fields are declared as annotations, which silently degraded the
recovery prompt. `create_fallback_model` uses the same `model_fields` inspection so an
empty `decisions` / `macro_events` instance is always constructible.

## Provider-Specific Extraction Contracts

Extraction is not one uniform Instructor call. Each provider has a contract that
keeps the final turn a pure JSON turn, because a model that continues the tool
conversation returns prose or native tool syntax instead of a parseable payload —
which surfaces downstream as `decisions: []` even though the model never declined
to trade.

### DeepSeek — JSON-only final turn

`build_provider_extraction_args` appends an explicit user turn when
`provider == "deepseek"`:

```text
Based on the preceding evaluation and tool results, extract and structure the final
 trade decisions. Do NOT call any tools. Do NOT output tool-call syntax.
Respond with ONLY the raw JSON object matching this schema exactly:
<schema hint>
```

Without it, DeepSeek continues the tool conversation (imitating the flattened
history) and never emits JSON. The generic "append a user turn when the last message
is `assistant`/`model`" branch now applies only to `gemini` and `anthropic`.

### DeepSeek — no synthetic tool-call markers

`prepare_messages_for_instructor` in `core/llm/handlers/deepseek.py` no longer
flattens `tool_calls` into `[Tool Call: name(args)]` text. It:

- drops the raw `tool_calls` payload (API gateway 400 `missing field tool_call_id` risk),
- strips any `[Tool Call: ...]` span from assistant content via `_TOOL_CALL_MARKER_RE`
  (DeepSeek copies that exact syntax verbatim, with `<｜｜DSML｜｜>` separators, instead of
  emitting JSON),
- converts `tool` messages to `user` messages prefixed `[Tool Result: ...]` so the
  evidence survives,
- and drops an assistant turn that has no prose left after flattening — an empty
  assistant turn invites the model to continue it.

`has_valid_content` continues to ignore assistant turns that are empty or
marker-only, scanning earlier turns for real prose.

### MiniMax — OpenAI-compatible extraction

`extract_structured_response` short-circuits to `extract_with_minimax_openai` when
`provider == "minimax"`. The Anthropic-compatible endpoint returns MiniMax's native
`]<]minimax[>[<tool_call>` syntax for extraction prompts (`No text content in response`
→ `JSON extraction malformed-input work limit exceeded`), so extraction runs on
`MiniMaxClient.chat` (the OpenAI-format endpoint) instead of Instructor:

- **Payload** — a clean extraction-only system prompt (`_MINIMAX_EXTRACTION_SYSTEM_PROMPT`,
  omitting tool-loop `SEQUENCE RULE` instructions) plus a compacted user message
  (`MINIMAX_MAX_CONTEXT_CHARS = 60000`) that preserves the initial prompt context
  (`MINIMAX_INITIAL_CONTEXT_CHARS = 12000`), the earliest tool outputs
  (`get_portfolio_ledger`, `get_todays_news_menu` `source_id`s, kept in the first
  `MINIMAX_HISTORY_HEAD_CHARS = 16000` chars of the `=== Tool Execution History ===`
  block), and the trailing `MINIMAX_HISTORY_TAIL_CHARS = 32000` chars of tool results on
  newline boundaries, followed by an explicit *do not continue the tool conversation /
  do not emit tool-call syntax / return ONLY the raw JSON object matching this schema*
  instruction (with `build_schema_hint` inspecting Pydantic v2 `model_fields`).
- **Budget & Mode** — `max_completion_tokens=32768` (`MINIMAX_EXTRACTION_MAX_TOKENS`,
  accommodating MiniMax M3.1's 10k–14k reasoning token budget) and `response_format={"type": "json_object"}`.
- **Sanitization & Retry** — `sanitize_minimax_content` strips `think` blocks (including
  unclosed ones), `<tool_call>` / `<invoke>` blocks, `]<]minimax[>` markers, and stray
  `tool_call` / `invoke` / `ticker` / `content` / `parameter` tags before
  `try_parse_response`, with 1 bounded validation-recovery retry that echoes the previous
  output (first 2000 chars) plus a schema-feedback correction turn.
- **Failure** — after 2 failed attempts, logs `finish_reason`, `usage`, and the sanitized
  head (first 500 chars) and returns `[create_fallback_model(response_model)]` rather than raising.
- **Cleanup** — the client is always closed in a `finally` block.

The MiniMax *tool loop* still runs through the Anthropic SDK
(`handlers/anthropic.run_tool_loop`) against MiniMax's Anthropic-compatible base URL;
only the extraction step moved. See [[concepts/thinking-agents]] and
[[concepts/model-anomalies]].

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
- [[concepts/thinking-agents]] — per-provider thinking/extraction mode allocation
- [[concepts/model-anomalies]] — the DeepSeek and MiniMax failure modes these contracts resolve
- [[concepts/multi-track-autoresearch]] — the track resolution that drives experiment tool sets
