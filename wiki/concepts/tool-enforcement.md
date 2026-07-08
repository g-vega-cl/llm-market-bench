---
tags: [tools, hallucination, enforcement, validation]
category: concept
---

# Tool Enforcement & Hallucination Prevention

A 4-layer defense system preventing LLM hallucinations in tool usage and pricing.

## Layer 1: Pre-Prompt Strengthening

System prompt includes explicit instructions: prices are pre-injected, quantity
tools are mandatory for BUY/SELL, text-only claims = hallucination = rejection.
Few-shot examples show correct vs incorrect patterns.
- **Sequence Constraint Rule**: `SYSTEM_PROMPT_CONSTRAINTS_HEADER` (the immutable prompt header) contains a strict ordering constraint enforcing that all tool calls must be fully executed before the final structured JSON decision block is produced.

## Layer 2: Context Enhancement

Portfolio source-of-truth statement + held tickers quick reference + verified
market data block injected before LLM reasons.

## Layer 3: Post-Analysis Verification

Server-side scan of conversation history for actual `calculate_buy/sell_quantity`
function calls. Robust to formatting variances (normalizes whitespace, casing).
Ownership pre-validation catches SELL-on-unheld-ticker before verification.

- **Self-Correction Retry Loop**: If the LLM generates a BUY/SELL recommendation without executing the required tool call (a common failure pattern in models like `gemini-3.1-flash-lite` that return the structured response in their first turn), the engine intercepts this post-analysis. It appends a correction request directly to the unflattened conversation history and triggers a single-attempt retry loop of the provider's tool-calling sequence. A subsequent extraction is then performed. If the model executes the tool call on this retry turn, the trade is verified as valid rather than rejected.
  - **Gemini Role Mapping**: When retrying Gemini, the correction message appended to history with role `"assistant"` is translated to `"model"` right before passing to the `instructor` client. This prevents a `ValueError: Unsupported role: assistant` crash, because the Google GenAI SDK client only supports `"user"`, `"model"`, and `"system"` roles.
- **DeepSeek & Anthropic Message Preservation**: Because Anthropic/Claude models require content flattening, and DeepSeek models require message flattening (`prepare_messages_for_instructor`) for Instructor structured compatibility, their structured tool calling blocks are natively destroyed during these preparation steps. To prevent incorrect `REJECTED_TOOL_USAGE` rejections, the engine preserves a deep copy of the raw message history (`unflattened_messages`) right after the tool loops run (before any preparation/flattening occurs) and performs the post-analysis verification scan against this unflattened copy.
- **MiniMax Bypass & Cognitive Nudge**: The MiniMax-M3 simplified portfolio does not require native function calling or tool execution loops at execution time, so Layer 3 is entirely bypassed for MiniMax-derived trade signals. However, during the analysis phase, the model is nudged via a dedicated system prompt prefix to call the quantity calculation tools to ensure it remains cognitively aligned with real-time portfolio metrics.

## Layer 4: Structured Output Isolation

Deep-copy isolation prevents Instructor schema injection from polluting audit
logs. Execution authority means LLM specifies ticker + signal + allocation; the
system computes price, quantity, limit price server-side.

- **MiniMax Bypass**: Since MiniMax returns raw structured JSON (instead of using Instructor client tools), Layer 4 is bypassed. The system still computes price and quantity server-side to prevent price hallucinations.
- **Verifier Response Schema Normalization**: To prevent structured schema extraction crashes (e.g. `type object 'list' has no attribute 'model_json_schema'` when DeepSeek is run in `instructor.Mode.MD_JSON` mode), the Verifier Agent's `response_model` is dynamically set. Gemini uses `list[VerificationResult]` (to support multi-block tool calling), while other providers (OpenAI, Anthropic, DeepSeek) use `VerificationResult` directly. The output is normalized via `ensure_list` before downstream checks.
  - **Gemini Verifier Role Mapping**: Similar to the retry loop, any message with role `"assistant"` passed to the Verifier's `instructor` completion request is translated to `"model"` to adhere to Google GenAI SDK limitations.


## Price Hallucination Prevention

The system pre-fetches all relevant prices before analysis and injects them as
VERIFIED MARKET DATA. The LLM never produces price fields. If JIT price at
execution drifts >2% from injected price, trade is `REJECTED_STALE_QUOTE` (this drift rejection is bypassed for the MiniMax model to favor simulated instant execution).

## Related

- [[entities/engine]]
- [[entities/pipeline]]
- [[concepts/reasoning]]
- [[concepts/minimax-portfolio]]
