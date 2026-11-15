---
tags: [agent, workflow]
category: concept
---

# Agent Workflow

This page describes the mandatory Search/Plan/TDD sequence for all agents. The workflow ensures thorough research, structured planning, and test-driven development.

## Search First (QMD)

Before answering any question or starting any task, you must search the wiki using `qmd` (query, search, or vsearch). The wiki is the compiled project memory; do not rely on general knowledge.

## Plan First

Before making any code changes or executing multi-turn workflows, present a written strategy and wait for explicit approval. Do not "just fix it." This step includes the following sub-requirements:
- **Research & Strategy**: Stay in "Default" mode (avoid automated/restricted plan modes) to ensure full access to `qmd` and shell tools during research.
- **Wait for Approval**: Stop and wait for an explicit "Go ahead" before beginning the Execution phase.
- **Visual Terminal Planning**: Plans for non-trivial features, migrations, or design questions MUST follow the terminal-friendly visual planning guidelines defined in [[concepts/visual-planning]].

## TDD Requirement

Every implementation plan MUST include a step for creating a reproduction test first. Verification requires a test that fails without your change and passes with it.

## Code is Truth

Docs are hints. When they conflict, trust the code. Read the code before acting — don't assume.

## Observability

Prioritize tracebacks over raw error strings. Use `logger.exception("Contextual message")` in `except` blocks. This ensures the automated log audit system can perform root-cause analysis on failures.

## Deterministic Lifecycle Gates & Context Hygiene

Hard execution rules (blocking blanket `git add -A` / `git add .` staging, multiline `python3 -c`, and raw `.env` dumps) are enforced before command execution via `.agents/hooks.json` (`apps/engine/agent_pre_tool_gate.py`) in addition to `.husky/pre-commit`. Root `GEMINI.md` and `.agents/rules/*.md` files are kept strictly below 20,000 bytes (`apps/engine/wiki_lint.py`) so no rule file is ever truncated by Antigravity's 24 KB per-file cap.

## Related

- [[concepts/project-linting]]
- [[concepts/visual-planning]]
- [[concepts/vertical-slice-islands]]
- [[entities/engine]]
- [[entities/agent-rules]]
- [[concepts/observability-standard]]
