---
tags: [gemini, project, mandates, workflow]
category: entity
---

# Gemini — Project-Level Mandates & Workflow Reference

This page documents the top-level instructions and operational rules for the LLM (Gemini) when working on this project. These mandates take precedence over any other instructions and must be followed at all times.

## Principles (MANDATORY)

1. **Search First (QMD)**: Before answering any question or starting any task, search the wiki using `qmd` (query, search, or vsearch). The wiki is the "compiled" project memory; do not rely on general knowledge.
2. **Read First Rule**: Before editing any file, read its full contents (or at minimum the relevant functions/classes) to understand existing structure, patterns, and edge cases.
3. **Lint & Test Gate**: After every code change, verify lint and coverage pass before marking work complete. The pre-commit hook will block commits with lint errors or low coverage. Run `ruff check` on changed Python files and `biome check` on changed TS files. Use `ruff check --fix` / `ruff check --fix --unsafe-fixes` / `biome check --write` to auto-fix before resorting to manual edits. A passing test suite with failing lint or low coverage is not done.

## Commit Message Protocol (MANDATORY)

All commit messages are strictly validated by `.husky/commit-msg` via `apps/engine/commit_msg_lint.py`. When drafting or suggesting git commits:

1. **Subject Line Format**: `<type>(<scope>): <description>` (e.g. `feat(daily-predictor): pass daily newsletter to predictor`)
   - **Valid `<type>`**: `feat`, `fix`, `perf`, `docs`, `refactor`, `style`, `test`, `build`, `ci`, `chore`, `revert`.
   - **Subject Length**: Must be strictly ≤ 72 characters recommended (hard limit ≤ 100 characters, ≥ 5 characters description).
2. **Body Requirement**:
   - Commits of type `feat`, `fix`, `perf`, and `refactor` **MUST include a body** (≥ 15 characters) explaining the context and changes.
   - Must contain a **blank line** between the subject and the body.
3. **Drafting Template**:
   ```bash
   git commit -m "<type>(<scope>): <short imperative subject under 72 chars>" -m "- <Bullet 1 explaining what changed>
   - <Bullet 2 explaining why or rationale>
   - <Bullet 3 mentioning tests and docs>"
   ```

## Precedence

- **GEMINI.md takes precedence over README.md** for LLM-facing instructions.
- **Wiki SCHEMA.md and index.md** take precedence for documentation conventions.
- **Code in `apps/engine/`** takes precedence over general Python patterns.
- **If a `.cursorrules` file exists**, its contents are treated as project-level mandates with priority just below GEMINI.md.

## Related

- [[entities/commit-msg-lint]]
- [[concepts/project-linting]]
- [[concepts/agent-workflow]]
