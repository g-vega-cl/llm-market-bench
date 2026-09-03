---
tags: [wiki, lint, quality, automation]
category: entity
---

# Wiki Linter

Automated quality assurance for the project wiki, with two layers: structural lint (fast, pre-commit) and LLM-powered deep lint (weekly, OpenRouter).

## Structural Lint

Runs on every commit via pre-commit hook (`apps/engine/wiki_lint.py`). Checks:
- Frontmatter completeness (tags, category)
- Broken wiki-links (cross-references to non-existent pages)
- Orphan pages (no inbound links from other pages or index)
- Index coverage gaps (pages missing from index.md)
- Codebase reference validation (verifies backticked code paths on disk)
- Configuration parity (verifies active models in `packages/config/models.json` and tools in `packages/config/tools.json` are documented)

Runs in ~20ms with no API cost.

## LLM Git Drift Auditor

Runs weekly via GitHub Actions (Saturday 10:00 ET) or manually (`apps/engine/wiki_lint_llm.py`). Compares recent code commits against the specific wiki pages documenting those subsystems to detect code-documentation drift.

Key features:
- **Event-Driven Scoping**: Queries `git log --since="7 days ago"` to find modified code/config files, skipping static pages that haven't changed.
- **Targeted Page Mapping**: Scores and selects only the 5-8 wiki pages directly linked or relevant to the changed code files.
- **Outcome Drift Rubric**: Evaluates candidate pages for stale architectural claims, invalid configuration defaults, and omitted subsystem documentation.
- **Immediate Fast-Path**: If no functional code changed that week, exits cleanly in 0.5s with zero LLM calls.

## Related

- [[concepts/project-linting]]
- [[entities/auto-wiki]]
- [[entities/engine]]
