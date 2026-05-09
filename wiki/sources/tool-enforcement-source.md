---
tags: [engine, hallucination, safety]
category: source
---

# Source: Tool Enforcement & Hallucination Prevention

Synthesized from `raw/docs/engine/TOOL_ENFORCEMENT.md`.

## Takeaways

- **Price Hallucination Elimination**: Prices are pre-injected into LLM prompts as "VERIFIED MARKET DATA". LLMs are forbidden from producing price fields, removing the possibility of price fabrication.
- **Mandatory Tool Usage**: BUY/SELL signals are rejected if the LLM fails to call the mandatory `calculate_buy_quantity` or `calculate_sell_quantity` tools. Textual claims of tool usage are not accepted.
- **Ownership Validation**: The system cross-references SELL signals with the actual portfolio state before execution to prevent selling unheld assets.
- **Provider-Specific Shims**: Specific handling for DeepSeek (thinking mode), Claude (token truncation), and Gemini (multi-tool calls) ensures consistent enforcement across models.

## Related

- [[entities/engine]]
- [[concepts/tool-enforcement]]
- [[concepts/reasoning]]
