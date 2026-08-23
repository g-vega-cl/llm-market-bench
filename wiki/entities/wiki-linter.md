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

Runs in ~20ms with no API cost.

## LLM Deep Lint

Runs weekly via GitHub Actions (Saturday 10:00 ET) or manually. Sends all wiki pages to DeepSeek via OpenRouter to check for:
- Contradictions between pages
- Stale claims (outdated code references)
- Missing concept pages
- Data gaps and thin pages

Recent improvements:
- **Reasoning Token Headroom & Flash Model Default** (2026-08-16): Switched default deep lint model to DeepSeek v4 Flash (`deepseek/deepseek-v4-flash`), increased response token budget (`max_tokens: 16384`), and capped reasoning tokens (`max_tokens: 4096`) to prevent chain-of-thought token exhaustion on large prompt payloads without sending unsupported effort levels.
- **Improved Error Handling** (2026-08-16): HTTP errors from OpenRouter now extract and surface the API's error message (e.g., invalid reasoning effort) instead of a generic status code, aiding debugging.
- **File manifest injection** (2026-07-10): the prompt now includes a JSON manifest of all wiki files, preventing false-positive "missing page" errors caused by text truncation.
- **Increased input size**: max input raised from 75k to 120k chars to accommodate more files.

## Related

- [[concepts/project-linting]]
- [[entities/auto-wiki]]
- [[entities/engine]]
