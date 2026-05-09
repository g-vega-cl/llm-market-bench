---
tags: [engine, attribution, overlap]
category: source
---

# Source: Agent-Specific Semantic Overlap

Synthesized from `raw/docs/engine/agent-specific-semantic-overlap.md`.

## Takeaways

- **Multi-Agent Independence**: The redundancy check is scoped per agent. One agent trading a ticker does *not* block another agent from trading it.
- **Overtrading Prevention**: Prevents a single agent from repeatedly trading the same semantic concept within a short window, encouraging diverse portfolio activity.
- **Implementation**: Uses pgvector similarity search filtered by `model_name` to find recent related decisions by the same agent.

## Related

- [[concepts/consensus]]
- [[concepts/tool-enforcement]]
- [[entities/engine]]
