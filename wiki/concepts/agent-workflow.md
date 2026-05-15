---
tags: [workflow, orchestration, mandates]
category: concept
---

# Agent Workflow

The project enforces a strict procedural sequence for all AI agents to ensure safety, consistency, and alignment with the codebase's current state.

## The Sequence

1. **Search First (QMD)**: Before answering any question or starting any task, search the wiki using `qmd`. The wiki is the "compiled" project memory. Relying on general model knowledge is forbidden if local documentation exists.
2. **Plan First**: Before making any code changes or executing multi-turn workflows, present a written strategy to the user. Do not proceed until explicit approval is granted.
3. **TDD First**: Every implementation plan must include a step for creating a reproduction test (Red-Green-Refactor). Verification requires a test that fails without the change and passes with it.

## Rationale
This workflow prevents "hallucinated" solutions that ignore existing architectural patterns and ensures that every change is empirically verified via the automated test suite.

## References
- [[index]]
- [[log]]
- `AGENTS.md` (Project Root)
