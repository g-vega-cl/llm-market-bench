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
    - **Fail-safe Recovery**: The platform's analysis and verification pipelines still use `prepare_messages_for_instructor()` to sanitize `reasoning_content` from non-tool messages to prevent Instructor validation confusion. Additionally, during final Instructor extraction, `prepare_messages_for_instructor()` cleanly flattens all `tool_calls` and tool response messages into standard user/assistant plain-text messages. Since Instructor's DeepSeek `Mode.MD_JSON` does not use tools for extraction, this prevents the DeepSeek API Gateway 400 `missing field tool_call_id` deserialization error while preserving all intermediate tool results in the prompt. If the `has_valid_content()` check fails on a final step, a corrective JSON recovery prompt is appended in-context to force JSON production in a follow-up turn.
  - *MiniMax `<think>` Tag Clash & Empty Response*: MiniMax-M3 is a reasoning model that embeds its internal chain-of-thought in `<think>...</think>` tags inside the `content` field. The platform's JSON repair function (`_repair_json_string`) searches for the first `{` character. If the `<think>` block contains any curly braces, it slices the string inside the reasoning block, producing malformed output that fails JSON parsing and logs an empty response. Furthermore, `None` responses from content filtering or empty replies caused attribute errors during string stripping.
  - *MiniMax Mitigation*: The engine now strips `<think>...</think>` blocks (including unclosed ones if the token limit is hit mid-thought) *prior* to JSON repair, safe-coerces `None` content to `""`, and explicitly passes `response_format={"type": "json_object"}` to enforce structured JSON output at the MiniMax API level.
  - *Detection*: Schema validation failure or missing content at the handler level (e.g., Pydantic validation errors).
- **Zero Decision Generation / Tool Violations**: The model consistently produces zero trading decisions on high-volatility days where action is statistically expected, indicating over-alignment, or recommends actions without performing the required pre-requisite tool calls.
  - *Gemini-3.1-flash-lite Zero Decision Anomaly*: Consistently returning zero trades or failing to execute necessary calculations during major macro shifts.
  - *Gemini-3.1-flash-lite Built-in Tool Anomaly*: Previously, the Gemini API threw a `400 INVALID_ARGUMENT` error when attempting to use Google's built-in tools (such as web search) in combination with client-side function calling, complaining: *"Please enable tool_config.include_server_side_tool_invocations to use Built-in tools with Function calling"*. This triggered an immediate fallback to basic (non-tool) analysis, causing recommendations to be rejected by the `HARD ENFORCEMENT` guardrail.
  - *Mitigation*: The platform now detects if the SDK config supports the flag and properly configures `tool_config = types.ToolConfig(include_server_side_tool_invocations=True)` inside `GenerateContentConfig` during multi-tool execution. This nests the flag correctly according to the strict `google-genai` SDK Pydantic schema and completely resolves the 400 error. It also preserves and echoes back Gemini's unique function call `id` within subsequent `FunctionResponse` parts, which completes tool context circulation and resolves all multi-turn circulation errors.
  - *DeepSeek Tool Call Narration Anomaly*: When DeepSeek v4 models run with `thinking: {"type": "enabled"}` in the same API request body where `tools` are provided, the model narrates/hallucinates its tool-calling intent inside the reasoning block but fails to emit the actual structured `tool_calls` payload object. This causes the loop to exit early with 0 executions, leading to downstream `HARD ENFORCEMENT` trade rejections.
  - *DeepSeek Mitigation*: The platform disables `thinking` mode during the tool loop calls since these are pure info-gathering/calculation operations that do not benefit from thinking mode and are prone to narration confusion. However, `thinking` mode is explicitly enabled during the final extraction phase so the model can use its full reasoning capacity to formulate the final trade decisions.
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
