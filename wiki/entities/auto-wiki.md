---
tags: [auto-wiki, documentation, git, staging, automation]
category: entity
---

# Auto-Wiki

`apps/engine/auto_wiki.py` (invoked by `scripts/auto-wiki.sh`) generates and updates wiki documentation from staged git diffs. It runs as a blocking pre-commit step: if documentation generation fails, the commit is blocked.

## LLM Tier Chain

`generate_with_fallback(prompt, args, api_key)` runs three tiers in order and returns the first usable result:

1. **free-llm-proxy (`auto-go`)** — the in-repo proxy (see [[entities/free-llm-proxy]]). `_proxy_available()` calls `get_proxy_config()`; when that raises `RuntimeError` (no `FREE_PROXY_MASTER_KEY` while `FREE_LLM_PROXY_URL` points at a remote proxy) the tier is skipped with a stderr note instead of aborting, so a fresh clone holding only an OpenRouter key still documents. Model: `WIKI_DOC_PROXY_MODEL` / `--proxy-model` (default `auto-go`).
2. **OpenRouter primary** — `WIKI_DOC_MODEL` / `--model` (default `~deepseek/deepseek-flash-latest`), used only when `OPENROUTER_API_KEY` resolves from the environment or the macOS keychain item `openrouter-api-key`.
3. **OpenRouter free backup** — `WIKI_DOC_FREE_MODEL` / `--free-model` (default `openrouter/free`), skipped when it equals the primary model.

The proxy leads because its `auto-go` alias walks free providers before the paid `opencode-go` tail, making it the cheap path; OpenRouter is the backup. If all three tiers fail, `generate_with_fallback` prints an error and calls `sys.exit(1)` — the commit is blocked because documentation is required.

### Budgets and timeouts

- `MAX_OUTPUT_TOKENS = 65536` is the `max_tokens` sent on both the proxy and OpenRouter calls. The proxy clamps it down per provider (groq stays at 32k), so asking for 64k only raises what the larger providers may return.
- `PROXY_TIMEOUT_SECONDS` (env `WIKI_DOC_PROXY_TIMEOUT_SECONDS`, default `180`) bounds the proxy tier's HTTP request. It must exceed free-llm-proxy's internal `FREE_PASS_DEADLINE_SECONDS` (120s) + `PAID_PASS_DEADLINE_SECONDS` (45s) = 165s so `auto-go` can finish its full free-to-paid cascade instead of aborting early. A healthy `auto-go` answers a documentation prompt in seconds; a saturated free pool walks every provider and takes minutes, and this runs inside the pre-commit hook.
- `OPENROUTER_TIMEOUT_SECONDS` (env `WIKI_DOC_OPENROUTER_TIMEOUT_SECONDS`, default `90`) bounds each OpenRouter fallback call.
- Both HTTP calls run through `_post_with_wall_clock`, which executes `requests.post` in a daemon thread and enforces a strict wall-clock ceiling. Standard `requests` timeouts only cap connect/idle gaps, so a trickling or stalled upstream can hang longer; this aborts at the deadline with `requests.Timeout`.
- OpenRouter calls are recorded through `core/llm/openrouter_calls.py#log_requests_call` (`purpose="engine:auto_wiki"`) into the shared free-llm-proxy audit SQLite database, including model, prompt preview, response status, and latency. The proxy tier is already audited by the proxy itself, so it is not duplicated by the engine.

## Staging Contract

The script tracks exactly which files it writes and re-stages only those files, avoiding accidental inclusion of unrelated concurrent wiki edits.

- `scripts/auto-wiki.sh` creates a temp `WRITTEN_LIST` file and passes `--written-files-out "$WRITTEN_LIST"` to `auto_wiki.py`.
- `auto_wiki.py` records every page it creates/updates/deletes into that list.
- After generation, the shell script re-stages only the listed files (`git add -- "$file"`), never sweeping the whole `wiki/` tree.
- If the "How It Works" page is recompiled (`apps/engine/scripts/compile_how_it_works.py`), the generated `apps/web/src/config/how-it-works.json` is appended to the written list on success.

This prevents a commit from capturing unrelated wiki edits made concurrently in the working tree.

## Code Reference Normalization

`auto_wiki.py::normalize_code_references` rewrites code references in generated pages so paths are relative to the repository root. Engine script references like `apps/engine/scripts/update_prices.py` are expanded to `apps/engine/scripts/update_prices.py`, while non-engine paths (e.g. `scripts/auto-wiki.sh`) are left intact. `write_new_page` applies this normalization before writing.

## Related

- [[concepts/wiki-synchronization]] — keeping wiki pages in sync with code
- [[entities/wiki-linter]] — structural lint on commits
- [[concepts/code-reference-validation]] — validating code references in docs
- [[entities/free-llm-proxy]] — the `auto-go` alias that serves the primary documentation tier
- [[concepts/auto-go-utility-llm]] — the engine-side consolidation that routes utility LLM calls through the same proxy
