---
tags: [source, redundancy, agent-specific, overlap]
category: source
source: docs/engine/agent-specific-semantic-overlap.md
---

# Source: Agent-Specific Semantic Overlap

Ensures semantic redundancy checks are scoped per-agent, preserving independent
decision-making.

Key details:

- **Problem**: Previously, overlap compared trades across ALL agents — if Claude traded NKE, Gemini was blocked. Violated multi-agent principle.
- **Solution**: `find_similar_decision()` and `find_similar_vector()` filter by `model_name`. Each agent's trades only compared against its own recent trades.
- **Result**: Claude blocked from repeating NKE, Gemini can still trade it independently.
- **No migrations needed**: `model_name` column already existed in `decisions` table.
