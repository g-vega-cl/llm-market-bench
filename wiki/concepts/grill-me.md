---
tags: [skill, interviewing, requirements, design-tree, agent-workflow]
category: concept
---

# Grill Me

**Grill Me** is an agent skill that turns the agent into a relentless interviewer: instead of guessing at requirements, it walks the user down every branch of the design tree until both parties share one understanding of the task. It is registered at `.agents/skills/grill-me/SKILL.md` and invoked explicitly with `/grill-me`.

## Why It Exists

Ambiguous tasks get silently resolved by the model's median assumptions, which is exactly the failure mode [[concepts/creative-ideation]] attacks from the other direction. Grill Me front-loads the ambiguity: every decision that constrains later decisions is surfaced and settled *before* any code or plan file is written.

## Execution Model

The skill is a structured interview, not a checklist:

1. **One question at a time** — never batch questions; each answer reshapes the next question.
2. **Explore before asking** — if the codebase can answer it, read the codebase instead of spending a user turn.
3. **Recommend an answer first** — every question ships with the agent's proposed answer, so the user can confirm rather than compose from scratch.
4. **Dependency order** — ask the question whose answer constrains the most downstream questions first, resolving the design tree top-down.
5. **No implementation until shared understanding** — no code, no plan files, no edits while the interview is open.
6. **Keep grilling** — the first acceptable answer is not the end; the tree is only done when it is fully resolved.

## Design-Spec Guardrail

Before proposing any UI or interaction model, the skill requires checking `.agents/rules/design-spec.md` (GEMINI.md Principle 11). Banned patterns — floating tooltips, popovers, SVG title hovers, modals, accordions — must never be proposed during the interview, which keeps the design tree from growing branches that violate the project's design system (see [[entities/design-system]]).

## Closing

When the tree is resolved, the skill summarizes the decisions made and the open questions that remain, then waits for explicit approval before executing (GEMINI.md Plan First).

## Related

- [[concepts/creative-ideation]] — the divergent counterpart: generate 10 non-obvious options before converging
- [[concepts/agent-workflow]] — Mandatory Search/Plan/TDD sequence the interview feeds into
- [[concepts/visual-planning]] — terminal-native planning framework used after the interview
- [[entities/agent-rules]] — project-level mandates including Plan First and the design spec
- [[entities/design-system]] — the component and interaction rules the interview must respect
