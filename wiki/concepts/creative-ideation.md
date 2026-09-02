---
tags: [ideation, brainstorming, architecture, agent-skill]
category: concept
---

# Creative Ideation Skill

Creative ideation is an agent workflow skill designed to break past median LLM default answers when designing new features or exploring architecture.

## Why this matters

Language models sample high-probability tokens first, which defaults to predictable, median textbook patterns. Asking for more ideas without constraints often yields minor variations of the first suggestion.

By requiring the agent to exhaust the 3 obvious answers first, the model clears standard patterns from its immediate context. Forcing 10 distinct, non-repeating alternatives pushes the model into the long tail of its conceptual network to uncover simpler, lateral, or unexpected architectures.

## Execution Model

The skill is registered at `.agents/skills/creative-ideation/SKILL.md` and executes in four steps:

1. **Drain the 3 obvious ways**: State the 3 most direct, textbook ways to build the feature.
2. **Generate the next 10 distinct ways**: Produce 10 non-obvious alternatives forbidden from repeating or tweaking the first 3.
3. **Surface 5 downstream levers**: Highlight 5 second-order questions, failure modes, or opportunities exposed by the 10 ideas.
4. **Checkpoint**: Await user direction before proceeding to planning or code.

## Related

- [[concepts/agent-workflow]] — Mandatory Search/Plan/TDD sequence
- [[concepts/visual-planning]] — Terminal-native visual planning framework
- [[concepts/wayfinder]] — Wayfinder planning methodology
- [[concepts/unslop-editing]] — Unslop prose editing skill
