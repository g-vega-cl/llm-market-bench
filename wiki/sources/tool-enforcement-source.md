---
tags: [source, tools, enforcement, hallucination]
category: source
source: docs/engine/TOOL_ENFORCEMENT.md
---

# Source: Tool Enforcement & Hallucination Prevention

Detailed in [[concepts/tool-enforcement]].

Key details:

- Four categories of observed hallucination: tool usage claims without function calls, ownership errors, price hallucination
- Price hallucination fully eliminated by pre-injected market data approach
- Staleness safeguard: if JIT price drift exceeds threshold → REJECTED_STALE_QUOTE
- DeepSeek thinking mode handler clears `reasoning_content` from non-tool-call messages
- Claude `max_tokens` raised from SDK default to prevent mid-tool-call truncation
- Gemini multi-function-call uses `List[Model]` pattern and `Mode.GENAI_TOOLS`
