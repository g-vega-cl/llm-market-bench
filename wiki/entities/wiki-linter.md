---
tags: [linting, wiki, documentation, pre-commit]
category: entity
---

# Wiki Linter

Automated quality assurance for the project wiki. Combines two layers: a fast structural linter that runs on every commit, and a weekly LLM-powered deep lint for semantic contradictions and stale claims.

## Structural Lint (`wiki_lint.py`)

Executed via pre-commit hook in under 20ms. Checks:
- **Frontmatter completeness**: ensures every page has `tags` and `category`.
- **Broken wiki-links**: validates that all wiki-style cross-references point to existing pages.
- **Orphan detection**: flags pages with no incoming links (excluding scaffold files).
- **Index coverage** (optional): confirms all pages are listed in `index.md`.
- **Code reference validation** (NEW): scans page content for backticked or linked paths under `apps/`, `packages/`, `scripts/`, `supabase/`, `wiki/`, `.github/` and verifies they exist on disk. Prevents stale documentation references. Implemented via `validate_codebase_references()` in `wiki_lint.py`, with exclusions for template files and placeholders.

Errors are reported with tags like `[orphan]`, `[broken-link]`, `[broken-code-ref]`.

## LLM-Powered Deep Lint (`wiki_lint_llm.py`)

Runs weekly via GitHub Actions (Saturday 10:00 ET) or manually. Sends all wiki pages to an LLM (DeepSeek or other via OpenRouter) to detect:
- Contradictions between pages
- Stale claims outdated by recent code changes
- Missing concept pages or weak cross-references
- Data gaps and thin pages

Recent improvements:
- **File manifest injection** (2026-07-10): the prompt now includes a JSON manifest of all wiki files, preventing false-positive "missing page" errors caused by text truncation.
- **Increased input size**: max input raised from 75k to 120k chars to accommodate more files.

## Files

- `apps/engine/wiki_lint.py` – structural linter
- `apps/engine/wiki_lint_llm.py` – LLM-based deep lint
- `apps/engine/tests/test_code_reference_validation.py` – unit tests for path validation

## Related

- [[concepts/project-linting]]
- [[concepts/code-reference-validation]]
- [[entities/auto-wiki]]
