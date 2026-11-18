---
tags: [auto-wiki, documentation, automation]
category: entity
---

# Auto-Wiki Documentation Generator

An automated system that reads staged git diffs and generates wiki documentation via LLM. It runs as part of the pre-commit hook, analyzing code changes and producing new entity pages, concept pages, log entries, and index updates. A failing run blocks the commit — documentation is treated as a required artifact, not an optional nicety.

## Architecture

The auto-wiki system consists of two components:

- **`apps/engine/auto_wiki.py`** — Python script that collects the staged diff, sends it to an LLM (OpenRouter → free-llm-proxy fallback), parses the JSON response, and writes wiki files
- **`scripts/auto-wiki.sh`** — Bash wrapper called from `.husky/pre-commit` that captures the diff, invokes the Python script, and re-stages any wiki changes

## Diff Filtering (`filter_diff`)

`filter_diff(diff_content)` splits the staged diff into per-file blocks and drops any block whose path matches the skip list, so the model never spends its token budget on generated output or on documentation that is itself derived from the code diff:

- **Build artifacts and generated output** — `dist/`, `build/`, `.map`, lockfiles, and other generated paths.
- **Documentation inputs** — ` a/wiki/`, ` a/raw/`, ` a/knowledge-db/`, and ` a/docs/`. Pages are regenerated from the code diff, so sending their full text (often >15k chars) only truncates the model response and blocks the commit.

## LLM Integration

The script implements a 3-tier resilient fallback architecture:

1. **OpenRouter Primary** — uses `~deepseek/deepseek-flash-latest` by default, configurable via `WIKI_DOC_MODEL` env var
2. **OpenRouter Free Backup** — if the primary model fails or is rate-limited, automatically falls back to `openrouter/free` (configurable via `WIKI_DOC_FREE_MODEL`)
3. **free-llm-proxy (Last Resort)** — if both OpenRouter models fail, falls back to the in-repo `apps/free_llm_proxy/` over its OpenAI-compatible API. Base URL comes from `FREE_LLM_PROXY_URL` (default `https://llm.clvg.uk/v1`), the bearer key from `FREE_PROXY_MASTER_KEY`, and the model from `WIKI_DOC_PROXY_MODEL` (default `auto-go`). A loopback proxy URL (`127.0.0.1`, `localhost`, `::1`) is accepted without a master key so a local `free_llm_proxy` instance stays usable.

Every tier is remote. An earlier on-device 31B-model tier was removed: it demanded tens of GB of RAM and a populated local model store, so on a clean checkout it always failed and blocked the commit anyway. Tier 3 now costs zero local GPU/RAM and reuses the same proxy the engine already routes through.

The OpenRouter API key is resolved from the `OPENROUTER_API_KEY` environment variable or the macOS keychain item `openrouter-api-key`.

### Proxy Call Parameters

`call_free_proxy` posts an OpenAI-compatible payload to `{base_url}/chat/completions` with `temperature: 0.2`, `max_tokens: 32768`, and `response_format: {"type": "json_object"}`, using a 180-second timeout. A `null` content response raises an error noting that all upstream providers may be exhausted. The fallback model is selectable via the `--proxy-model` CLI flag (default `auto-go`).

### Token Budget

`call_openrouter` requests `max_tokens: 32768` with a `reasoning.max_tokens` budget of `4096` and `response_format: {"type": "json_object"}`. The generous completion ceiling exists because a single run can emit several full wiki pages plus index entries; a smaller ceiling truncated the JSON response mid-object and failed the parse.

## Wikilink Sanitization

LLMs frequently emit file paths as wiki links — e.g. ``packages/config/recipe-naming.json`` or ``push_schema.py``. The structural linter ([[entities/wiki-linter]]) resolves every `target` to a wiki page, so a file-path link has no page behind it and fails the pre-commit lint with a broken-link finding. Two guards run on every page body inside `write_new_page()` before the file is written, in this order: `delink_missing_pages(sanitize_wikilinks(content))`.

### `sanitize_wikilinks(content)`

Matches `...` targets whose final segment carries a known source/config extension (`.json`, `.yaml`/`.yml`, `.py`, `.ts`/`.tsx`, `.sql`, `.md`, `.sh`, `.toml`, `.cfg`, `.ini`) and rewrites them as inline code (`` `packages/config/recipe-naming.json` ``). Genuine page links such as `[[entities/recipe-studio]]` and `[[concepts/state-machines]]` are left untouched, so cross-references keep working.

### `delink_missing_pages(content)`

The generator occasionally cites a page it never creates. For each remaining `target`, the alias segment (after `|`) is stripped, a `.md` suffix is added when absent, and the target is checked against `WIKI_DIR`. A link whose page exists is preserved verbatim; a link with no page behind it is replaced by its bare target text, so the reference survives as prose instead of failing the lint.

This keeps auto-generated pages lint-clean without requiring the LLM to distinguish file paths from page slugs or to remember which pages it actually created.

## Safety & Design

- **Zero Local Compute**: No tier loads a model on the committing machine. The proxy tier is a plain HTTPS call, so contributors need neither a GPU nor a multi-GB model store to commit — `scripts/auto-wiki.sh` no longer starts or kills any local inference server.
- **Blocking by Design**: `.husky/pre-commit` invokes `scripts/auto-wiki.sh` without `|| true`, and the script exits non-zero when every LLM tier fails, so an undocumented code change cannot slip through silently.
- **Path traversal protection**: The `write_new_page` function validates that the target path stays within the `wiki/` directory
- **Dry-run mode**: `--dry-run` prints the LLM response without writing files
- **Skip logic**: Only triggers when staged files include non-documentation changes (skips wiki/raw/docs-only commits)

## Related

- [[entities/engine]] — the Python engine that hosts the script
- [[entities/wiki-linter]] — the structural lint that rejects file-path wikilinks
- [[concepts/rag-strategy]] — context injection patterns used in the system prompt
- [[concepts/tool-enforcement]] — similar pattern of LLM output validation
