---
name: grill-me
description: Interview the user relentlessly about a task until you share one understanding, walking the design tree one decision at a time. Invoke explicitly with /grill-me.
disable-model-invocation: true
---

# Grill me

The user has requested that you interview them about every aspect of their task until you have reached a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

## Guidelines

- Ask the questions one at a time.
- If a question can be answered by exploring the codebase, explore the codebase instead of asking the user.
- Use the `clarify` tool to ask the user questions, putting your recommended answer first.
- Resolve decisions in dependency order: ask the question whose answer constrains the most later questions first.
- Do not implement, write plan files, or change code until the interview reaches a shared understanding.
- Keep grilling until the design tree is fully resolved. Do not stop at the first acceptable answer.
- Before proposing any UI or interaction model, check `.agents/rules/design-spec.md` (GEMINI.md Principle 11). Never propose banned patterns (floating tooltips, popovers, SVG title hovers, modals, accordions) during the interview.
- When the interview concludes, summarize the decisions made and the remaining open questions, then wait for explicit approval before executing (GEMINI.md Plan First).
