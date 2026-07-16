---
tags: [commit, lint, conventional-commits, git]
category: entity
---

# Commit Message Lint

A pre-commit hook (`commit-msg`) that enforces [Conventional Commits](https://www.conventionalcommits.org/) formatting for all commit messages. Implemented in `apps/engine/commit_msg_lint.py`.

## Enforcement Rules

- **Subject line** must match `<type>(optional-scope): <description>` format
- **Valid types**: `feat`, `fix`, `perf`, `docs`, `doc`, `refactor`, `style`, `test`, `build`, `ci`, `chore`, `revert`
- **Body required** for `feat`, `fix`, `perf`, and `refactor` commits (minimum 15 characters)
- **Subject length**: minimum 5 characters, maximum 100 characters
- **Blank line** required between subject and body
- **Merge and revert commits** are whitelisted and bypass validation

## Integration

Installed as a Husky hook at `.husky/commit-msg`, which calls the Python script with the commit message file path. The hook blocks commits that don't conform, providing clear error messages and examples.

## Related

- [[concepts/project-linting]]
- [[entities/ruff-linter]]
- [[entities/biome-linter]]
