---
tags: [context-injection, prompt-design, system-prompt, pull-based]
category: concept
---

# System-Heavy Prompt

A design pattern where the trading prompt is structured to be system-heavy and pull-based, meaning the model is given a rich, static system context and explicitly pulls in dynamic data (e.g., via tool calls) rather than having everything pre-injected. This contrasts with push-based approaches that stuff all context into the prompt upfront.

## Why It Matters

Keeps prompts within context limits, reduces token waste, and improves response reliability by letting the model request only what it needs per turn. Aligns with the project's tool-first agency and RAG strategy.

## Relationship to Other Pages

- [[entities/pipeline]] — uses interactive pull-based tool loops where trading agents query market APIs on demand
- [[entities/daily-market-predictor]] — utilizes deterministic push-based context injection, pre-compiling all macro, options, and gap metrics into `market_context` for model inference and training auditability
- [[entities/tool-registry]] — canonical registry of pull-based agent tools
- [[concepts/rag-strategy]] — tiered context injection
- [[concepts/tool-first-agency]] — model-driven tool use
