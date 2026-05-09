---
tags: [wiki, karpathy, audit]
category: interaction
---

# Interaction: Wiki "Proper Setup" Audit

**Date**: 2026-05-15
**Participants**: Jules (AI), Human User

## Question

What constitutes a "properly set up" Karpathy-style LLM wiki for this project?

## Answer

A properly set up wiki follows the pattern established by Andrej Karpathy: a persistent, structured knowledge base where information compounds over time. Key elements include:

1. **`raw/` vs `wiki/` Separation**: Immutable source documents live in `raw/`, while synthesized, interlinked knowledge lives in `wiki/`.
2. **Synthesized Sources**: Every document in `raw/` should have a corresponding page in `wiki/sources/` that captures "why it matters" and key takeaways, providing a provenance trail.
3. **Entity & Concept Mapping**: Knowledge is organized into "Entities" (components like `engine`, `web-app`) and "Concepts" (ideas like `consensus`, `tool-enforcement`).
4. **Interlinking**: Heavy use of cross-references to create a dense graph of knowledge.
5. **Compounding Knowledge**: Interactions and Q&A sessions are "promoted" to wiki pages in `wiki/interactions/` to ensure knowledge doesn't evaporate between sessions.
6. **Automated Linting**: Structural and LLM-powered linting ensures the wiki remains healthy, linked, and free of contradictions.

## Takeaways

- Wiki is the primary knowledge layer; `raw/` is for auditability.
- Avoid content duplication; focus on synthesis.
- Use the wiki to "teach" future LLM sessions about the project's history and logic.

## Related

- [[SCHEMA]]
- [[sources/project-overview-source]]
