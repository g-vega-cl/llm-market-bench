---
tags: [engine, testing, quality]
category: source
---

# Source: Engine Testing Strategy

Synthesized from `raw/docs/engine/testing.md`.

## Takeaways

- **Zero Warning Policy**: Strict adherence to a warning-free test suite to ensure developer focus and catch regressions early.
- **Mocking at the Boundary**: Uses isolated unit tests for LLM handlers that mock the raw client rather than SDK internals, making tests immune to library updates.
- **Dependency Injection**: Favors DI for analysis functions, allowing for clean unit testing without complex internal patching.
- **Reasoning Traces**: Every LLM interaction is logged and auditable via the `/reasoning` dashboard, providing a complete "thought trail" for every trade.

## Related

- [[entities/engine]]
- [[concepts/tool-enforcement]]
