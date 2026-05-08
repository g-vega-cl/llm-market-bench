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

## Layer 4: Structured Output Isolation

Deep-copy isolation prevents Instructor schema injection from polluting audit
logs. Execution authority means LLM specifies ticker + signal + allocation; the
system computes price, quantity, limit price server-side.

## Price Hallucination Prevention

The system pre-fetches all relevant prices before analysis and injects them as
VERIFIED MARKET DATA. The LLM never produces price fields. If JIT price at
execution drifts >2% from injected price, trade is `REJECTED_STALE_QUOTE`.

## Related

- [[entities/engine]]
- [[entities/pipeline]]
- [[concepts/reasoning]]
