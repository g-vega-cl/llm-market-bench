---
tags: [wiki, linting, quality, llm]
category: entity
---

# Wiki Linter

The Wiki Linter is a multi-stage quality assurance system that ensures the project wiki remains structural sound, interlinked, and semantically consistent.

## Components

### 1. Structural Lint (`apps/engine/wiki_lint.py`)
A fast, rule-based linter that checks for:
- **Missing Frontmatter**: Ensures all non-scaffold pages have valid YAML frontmatter (tags, category).
- **Broken Links**: Validates that all wiki links (using double brackets) resolve to existing files.
- **Orphan Pages**: Identifies pages that have no incoming links from other wiki pages.
- **Index Coverage**: Ensures all pages are referenced in `wiki/index.md`.

### 2. LLM Semantic Lint (`apps/engine/wiki_lint_llm.py`)
An LLM-powered auditor (typically using `deepseek/deepseek-v4-flash` via OpenRouter) that performs deep semantic analysis. It looks for:
- **Contradictions**: Conflicting claims across different pages.
- **Data Gaps**: Missing information that the project context implies should exist.
- **Stale Claims**: Outdated technical or architectural descriptions.
- **Weak Cross-references**: Semantic relationships that lack explicit links.

## Observability & Debugging

The LLM linter follows the project's **Observability Standards**:
- **Centralized Logging**: Uses the `engine` logger (configured in `apps/engine/core/config.py`).
- **Fail-Safe Parsing**: Robustly extracts JSON from LLM responses, even if wrapped in markdown blocks (e.g., ` ```json `).
- **Detailed Diagnostics**: On JSON parsing failures (common in CI/CD), it logs the **raw response content** and the **extracted string** to stderr. This allows for immediate root-cause analysis of empty responses or model refusals.

## Execution

### GitHub Actions
The linter runs weekly via `.github/workflows/wiki-lint.yml`. Findings are automatically converted into GitHub Issues labeled `wiki-lint`.

### Local Execution
```sh
# Structural lint only
python apps/engine/wiki_lint.py

# LLM lint (requires OPENROUTER_API_KEY)
python apps/engine/wiki_lint_llm.py --model "deepseek/deepseek-v4-flash"
```

## Related
- [[concepts/project-linting]]
- [[entities/auto-wiki]]
- [[concepts/observability-standard]]
