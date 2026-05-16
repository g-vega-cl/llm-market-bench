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
An LLM-powered auditor (typically using `deepseek/deepseek-v4-pro` via OpenRouter) that performs deep semantic analysis. It identifies contradictions, data gaps, stale claims, and weak cross-references.

- **Operational Status**: Fully operational as of 2026-05-16. 
- **Performance**: Capable of processing ~50 pages (~75k chars) in a single pass.
- **Reporting**: Automated GitHub Issue creation for any findings.

## Observability & Debugging

The LLM linter follows the project's **Observability Standards**:
- **Centralized Logging**: Uses the `engine` logger (configured in `apps/engine/core/config.py`).
- **Robust JSON Extraction**: Uses a combination of `re.finditer(r"\{", raw)` and `json.JSONDecoder().raw_decode` to surgically locate the first valid JSON object. This strategy handles duplicate JSON outputs, conversational prefaces, and trailing garbage that often cause standard `json.loads` or `strip()`-based approaches to fail.
- **Context Optimization**: LLM input is capped at 75k characters with `max_tokens` tuned to 4096 to prevent truncation and "Unterminated string" errors during high-volume linting.
- **Detailed Diagnostics**: On JSON parsing failures, it logs the **raw response content** to stderr. This allows for immediate root-cause analysis of empty responses, model refusals, or structural anomalies in GitHub Actions logs.

## Execution

### GitHub Actions
The linter runs weekly via `.github/workflows/wiki-lint.yml`. Findings are automatically converted into GitHub Issues labeled `wiki-lint`.

### Local Execution
```sh
# Structural lint only
python apps/engine/wiki_lint.py

# LLM lint (requires OPENROUTER_API_KEY)
python apps/engine/wiki_lint_llm.py --model "deepseek/deepseek-v4-pro"
```

## Related
- [[concepts/project-linting]]
- [[entities/auto-wiki]]
- [[concepts/observability-standard]]
