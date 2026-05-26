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

## Layer 2: Context Enhancement

Portfolio source-of-truth statement + held tickers quick reference + verified
market data block injected before LLM reasons.

## Layer 3: Post-Analysis Verification

Server-side scan of conversation history for actual `calculate_buy/sell_quantity`
function calls. Robust to formatting variances (normalizes whitespace, casing).
Ownership pre-validation catches SELL-on-unheld-ticker before verification.

- **Anthropic Message Preservation**: Because Anthropic/Claude models require content flattening into raw text strings for Instructor structured compatibility, their structured tool calling blocks (`tool_use`) are natively destroyed during this flattening block. To prevent incorrect `REJECTED_TOOL_USAGE` rejections, the engine preserves a deep copy of the raw message history (`unflattened_messages`) before flattening occurs and performs the post-analysis verification scan against this unflattened copy.
- **MiniMax Bypass**: The MiniMax 2.7 simplified portfolio does not require native function calling or tool execution loops. As such, Layer 3 is entirely bypassed for MiniMax-derived trade signals.

## Layer 4: Structured Output Isolation

Deep-copy isolation prevents Instructor schema injection from polluting audit
logs. Execution authority means LLM specifies ticker + signal + allocation; the
system computes price, quantity, limit price server-side.

- **MiniMax Bypass**: Since MiniMax returns raw structured JSON (instead of using Instructor client tools), Layer 4 is bypassed. The system still computes price and quantity server-side to prevent price hallucinations.

## Price Hallucination Prevention

The system pre-fetches all relevant prices before analysis and injects them as
VERIFIED MARKET DATA. The LLM never produces price fields. If JIT price at
execution drifts >2% from injected price, trade is `REJECTED_STALE_QUOTE` (this drift rejection is bypassed for the MiniMax model to favor simulated instant execution).

## Related

- [[entities/engine]]
- [[entities/pipeline]]
- [[concepts/reasoning]]
- [[concepts/minimax-portfolio]]
