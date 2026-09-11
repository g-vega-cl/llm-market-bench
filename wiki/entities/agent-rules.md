---
tags: [agent, rules, mandates, workflow]
category: entity
---

# Agent Rules and Instructions

The canonical source of truth for agent behavior, instructions, and operational commands is `GEMINI.md` at the repository root. `AGENTS.md` acts as an entry pointer directing all coding assistants to `GEMINI.md`.

This wiki page documents the role of `GEMINI.md` in the system architecture and its relationship to other project guidelines.

## Role and Authority

Root `GEMINI.md` is injected directly into agent context during pair-programming sessions. Its mandates take absolute precedence over default system prompts or autonomous workflows. When instructions conflict, trust the code and repository-root `GEMINI.md`.

### Precedence Hierarchy

1. **`GEMINI.md`** takes absolute precedence over general assistant defaults and external docs.
2. **Wiki `SCHEMA.md` and `index.md`** govern documentation conventions.
3. **Repository code** takes precedence over general framework assumptions.

## Core Mandates Summary

The full operational requirements are maintained in root `GEMINI.md`. Key principles link directly to deeper wiki concepts:

1. **Search First (QMD)**: Query the wiki using `qmd` before writing code or answering design questions.
2. **Plan First**: Present visual terminal plans (`[[concepts/visual-planning]]`) and wait for explicit approval before changing code.
3. **TDD First**: Every plan requires a reproduction test first (`[[concepts/agent-workflow]]`).
4. **Code is Truth**: Validate claims against working code.
5. **Observability**: Use structured tracebacks over opaque error strings (`[[concepts/observability-standard]]`).
6. **Hotspot Awareness**: Inspect churn forensics before modifying high-risk files (`[[concepts/code-hotspots]]`).
7. **API Integration Sanity**: Enforce strict HTTP error handling and realistic financial values.
8. **Tool-First, Agency-Driven Architecture**: Expose callable tools rather than injecting massive context tables (`[[concepts/tool-first-agency]]`).
9. **Zero Compute on Frontend**: Pre-materialize all heavy calculations in background pipelines (`[[concepts/zero-frontend-compute]]`).
10. **Vertical Slice Islands & File Size Ceiling**: 400 LOC soft ceiling, 800 LOC hard limit, colocated tests (`[[concepts/vertical-slice-islands]]`).
11. **Design System & UI Consistency**: Strict primitive consumption from `@llm-market-bench/ui-design-system` with zero arbitrary utility escapes (`[[entities/design-system]]`).

## Related

- [[concepts/agent-workflow]]
- [[concepts/visual-planning]]
- [[concepts/code-hotspots]]
- [[concepts/vertical-slice-islands]]
- [[concepts/zero-frontend-compute]]
- [[entities/design-system]]
- [[entities/commit-msg-lint]]
