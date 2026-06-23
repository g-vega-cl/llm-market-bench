---
tags: [minimax, execution, tool-calling, anthropic]
category: concept
---

# MiniMax Portfolio

MiniMax-M3 operates under a simplified execution model with a ±0.5% market order buffer and a dedicated Anthropic SDK handler for tool calling. This page documents the unique constraints and pipeline differences for the MiniMax provider.

## Simplified Execution Model

- **Market orders only** — MiniMax does not use limit orders. All trades are executed as market orders with a ±0.5% price buffer to account for slippage.
- **No web search** — The MiniMax pipeline disables web search (`enable_web_search=False`) to keep the analysis focused and deterministic.
- **Anthropic SDK handler** — As of 2026-06-18, MiniMax tool calling is routed through the Anthropic handler (`anthropic.run_tool_loop`) instead of the OpenAI handler. This provides native support for Anthropic-style message flattening, system message injection, and `max_tokens=32000`.

## Tool Calling

MiniMax uses the same tool definitions as other providers, but the underlying handler is now Anthropic. The handler manages the conversation loop, tool invocations, and response parsing. This change ensures consistent behavior with the Anthropic provider and simplifies maintenance.

## Related

- [[entities/pipeline]] — Full pipeline walkthrough
- [[concepts/tool-enforcement]] — 4-layer hallucination prevention
- [[concepts/execution]] — Trade validation and settlement
- [[concepts/rag-strategy]] — Tiered context injection
