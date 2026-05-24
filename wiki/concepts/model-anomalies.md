---
tags: [model, reliability, anomalies]
category: concept
---

# Model Anomalies

The platform continuously monitors LLM analysis output for anomalous behavior, including empty or malformed responses and zero decision generation. Tracking and documenting these patterns helps improve agent robustness, API failover strategies, and prompt engineering.

## Examples and Detection

Anomalies are flagged when model behavior violates expected output invariants. Common patterns include:

- **Empty JSON / Malformed Output**: The model returns unparseable JSON or empty objects `{}` when structured data is required.
  - *DeepSeek Empty Content Anomaly*: When DeepSeek v4 models run with thinking mode enabled (`"thinking": {"type": "enabled"}`), they sometimes generate rich internal reasoning inside `reasoning_content` but return a completely empty or whitespace-only main `content` string. This is caused by a cognitive formatting clash when forcing standard JSON Mode (`response_format={"type": "json_object"}` or `instructor.Mode.JSON`) alongside active reasoning.
  - *DeepSeek Mitigation (Root Resolution & Fail-safe)*: 
    - **Root Resolution**: The platform instantiates the DeepSeek client using **`instructor.Mode.MD_JSON`** rather than strict JSON Mode. By allowing the model to generate native markdown text containing a standard ` ```json ... ``` ` block alongside its natural reasoning, the formatting clash is avoided at the API level, completely eliminating empty response occurrences while preserving 100% of the reasoning/thinking performance.
    - **Fail-safe Recovery**: The platform's analysis and verification pipelines still use `prepare_messages_for_instructor()` to sanitize `reasoning_content` from non-tool messages to prevent Instructor validation confusion. Additionally, if the `has_valid_content()` check fails on a final step, a corrective JSON recovery prompt is appended in-context to force JSON production in a follow-up turn.
  - *MiniMax 01 Example*: Returning empty JSON arrays for Market Feeling analysis.
  - *Detection*: Schema validation failure or missing content at the handler level (e.g., Pydantic validation errors).
- **Zero Decision Generation / Tool Violations**: The model consistently produces zero trading decisions on high-volatility days where action is statistically expected, indicating over-alignment, or recommends actions without performing the required pre-requisite tool calls.
  - *Gemini-3.1-flash-lite Zero Decision Anomaly*: Consistently returning zero trades or failing to execute necessary calculations during major macro shifts.
  - *Gemini-3.1-flash-lite Built-in Tool Anomaly*: Previously, the Gemini API threw a `400 INVALID_ARGUMENT` error when attempting to use Google's built-in tools (such as web search) in combination with client-side function calling, complaining: *"Please enable tool_config.include_server_side_tool_invocations to use Built-in tools with Function calling"*. This triggered an immediate fallback to basic (non-tool) analysis, causing recommendations to be rejected by the `HARD ENFORCEMENT` guardrail.
  - *Mitigation*: The platform now detects if the SDK config supports the flag and enables `include_server_side_tool_invocations = True` during multi-tool execution. It also preserves and echoes back Gemini's unique function call `id` within subsequent `FunctionResponse` parts, which completes tool context circulation and resolves the 400 error completely.
  - *Guardrail Hard Enforcement*: When falling back to basic analysis or failing to use tools, models may still output trade recommendations. The engine enforces safety guardrails (e.g., `HARD ENFORCEMENT: Agent recommended BUY for <ticker> without executing 'calculate_buy_quantity' tool`) and automatically rejects these trades to prevent ungrounded or improperly sized transactions.
  - *Detection*: Post-analysis audit flagged when `len(decisions) == 0` for 3+ consecutive high-volatility days, or hard enforcement violations in the analysis log stream.

## Standard Operating Procedure (SOP)

When an anomaly is flagged, follow these resolution steps:

1. **Check Provider Status**: Verify if the LLM provider is experiencing an outage, high latency, or degraded service on their status page.
2. **Verify Context Window & Input**: Ensure the context payload (newsletters, market data) has not exceeded the model's actual maximum token limit or been truncated unexpectedly.
3. **Analyze Prompt Misalignment**: Check if recent prompt changes or auto-research ratchet updates caused the model to become overly conservative or confused.
4. **Failover**: If the issue is provider-side or persistent, manually switch the affected agent to a secondary provider (e.g., failover from Gemini to Claude) in the configuration.
5. **Document**: Record the anomaly, date, model version, and resolution in the incident log.

## Related

- [[concepts/reasoning]]
- [[entities/pipeline]]
