---
name: qmd-wiki
description: Search this repo's QMD-indexed wiki, git-history, and knowledge-db collections before answering project questions or planning code changes across Antigravity CLI, Pi, and Hermes.
---

# QMD Wiki Search

Use this skill before answering questions about `llm-market-bench` architecture, past decisions, runbooks, trading strategies, or UI conventions (`AGENTS.md` Search First rule).

## Procedure

1. **Query via QMD MCP first** (configured in both root `.mcp.json` and `.pi/mcp.json`):
   - Call `mcp__qmd__query` with `searches: [{ "type": "lex", "query": "..." }]`, `collections: ["wiki", "git-history", "knowledge-db"]`, and a clear `intent`.
   - Use `lex` (BM25) first so queries never contend with local Strata/Qwen GPU memory; add `vec` or `hyde` only if lexical search misses and VRAM is free.
2. **Read full pages, not snippets**:
   - Fetch full documents via `mcp__qmd__get` or `mcp__qmd__multi_get` (or `read_file` on `wiki/<path>.md`).
3. **Shell fallback under Node 24**:
   ```sh
   export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24
   qmd search "keywords" -c wiki -n 10
   qmd get "entities/engine.md"
   ```
- **Reverse code-to-wiki lookup**:
   - Before or after modifying source files, run:
     ```sh
     ./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py --affected-by apps/free_llm_proxy/router.py
     ```
   - Fallback catalog: `wiki/index.md` or `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py --topic-map`.

## Pitfalls

- QMD's native SQLite/tree-sitter modules require Node 22-25 (Node 26+ fails); always run under Node 24 (`nvm use 24`), which `.mcp.json` wraps automatically.
- Inside sandboxed shells without `~/.config/qmd` write access, prefer the `qmd` MCP tools or `wiki_lint.py --affected-by` / `read_file` on `wiki/index.md`.
- `qmd embed` runs asynchronously via the Fedora `systemd --user` timer; do not block fast git commits on GPU embedding.
