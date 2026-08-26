---
tags: [commit, lint, pre-commit, conventional-commits]
category: entity
---

# Commit Message Lint

A custom Python script (`apps/engine/commit_msg_lint.py`) that enforces [Conventional Commits](https://www.conventionalcommits.org/) format in the pre-commit hook (`.husky/commit-msg`).

## Validation Rules

- **Subject Line Format**: Must match `<type>(<scope>): <description>` pattern.
  - Valid types: `feat`, `fix`, `perf`, `docs`, `refactor`, `style`, `test`, `build`, `ci`, `chore`, `revert`.
  - Subject length: ≤ 100 characters, with description ≥ 5 characters.
- **Body Requirement**: For types `feat`, `fix`, `perf`, `refactor`, a body is mandatory with at least 15 characters and must have a blank line separating it from the subject.
- **Rejection**: Commits that fail validation are rejected entirely with a clear error message.

## Integration

- Invoked automatically by the `commit-msg` Git hook at `.husky/commit-msg`.
- Script location: `apps/engine/commit_msg_lint.py`.
- For full protocol details, see [[entities/gemini]].

## Related

- [[entities/gemini]] — project-level mandates including Commit Message Protocol
- [[concepts/project-linting]]
- [[entities/biome-linter]]
- [[entities/ruff-linter]]
