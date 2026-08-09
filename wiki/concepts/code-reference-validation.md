---
tags: [linting, validation, code-references, automation]
category: concept
---

# Code Reference Validation

Deterministic codebase path validation and linter scope analysis for wiki pages. Ensures every `[[]]` backtick path reference in wiki content points to a real file on disk, preventing broken links and stale documentation.

## How It Works

The structural lint (`apps/engine/wiki_lint.py`) runs as a pre-commit hook. The function `validate_codebase_references()` scans each wiki page for inline code references (text inside double backticks that looks like a file path). For each match, it:

1. Resolves the path relative to the repository root
2. Checks whether the file or directory actually exists on disk
3. Reports an error if the path does not exist

### Skipped Patterns

Certain paths are intentionally skipped to avoid false positives:

- **Placeholders with uppercase variables**: e.g., `YYYY-MM`
- **Placeholder markers**: `nonexistent`, `temp-broken`
- **Runtime environment files**: `.env`, `.venv` — these are typically gitignored and not present in the repo, but are valid references in documentation

## Test Coverage

Tests in `apps/engine/tests/test_code_reference_validation.py` cover both existing and missing file paths, including the skip logic for placeholders and runtime env paths (`.env`, `.venv`).

## Related

- [[concepts/project-linting]] — overall linting strategy
- [[entities/wiki-linter]] — structural and LLM wiki quality assurance
- [[entities/auto-wiki]] — automated wiki generation
