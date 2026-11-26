---
name: qmd-wiki
description: Search this repo's QMD-indexed wiki and knowledge base before answering project questions. Use for llm-market-bench architecture, decisions, history, runbooks, or any request where project knowledge matters; also use when setting up or diagnosing QMD access from Pi.
---

## When to Use

Use this skill before answering questions about this repo, including design, deployment, launch readiness, feature behavior, and documentation lookup. GEMINI.md Principle 1 makes QMD search mandatory; this skill is the Pi-side workflow.

## Procedure

1. Start with QMD. Prefer the MCP server tools:
   - `mcp__qmd__query` with `searches: [{ "type": "lex", "query": "..." }]`, `collections: ["wiki", "git-history", "knowledge-db"]`, and an `intent` that states what you want and what to avoid.
   - Add `vec` or `hyde` subqueries only when lexical search fails and model/GPU memory is available.
2. Read results with `mcp__qmd__get` or `mcp__qmd__multi_get`. Open the full page before relying on a fact. Snippets are leads.
3. Shell fallback uses the same index:

   ```sh
   export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24
   qmd search "keywords" -c wiki -n 10
   qmd get "entities/engine.md"
   qmd multi-get "concepts/*.md"
   ```

4. If QMD finds nothing, open `wiki/index.md` and follow its links. After wiki edits, run `qmd update && qmd embed` under Node 24, plus `wiki_lint.py`.
5. Cite the QMD path or docid when the answer depends on wiki content.

## Pitfalls

- `qmd query` and `qmd vsearch` load node-llama-cpp on CUDA and have failed here with `cudaMalloc failed: out of memory`. Use `qmd search` (BM25) or lex-only MCP subqueries first.
- QMD's native module needs Node 22-25. Node 26+ breaks it. Prefix shell commands with `nvm use 24`; the MCP wrapper already does this.
- Do not answer from snippets alone. Fetch the page with `get` or `multi-get`.
- `AGENTS.md` is only a pointer. The full instructions live in `GEMINI.md`, loaded into Pi through `.pi/APPEND_SYSTEM.md`.

## Verification

- `qmd ls` lists `wiki`, `git-history`, and `knowledge-db`.
- A lex QMD search returns matching paths and docids.
- Resolving `.pi/APPEND_SYSTEM.md` reaches the `GEMINI.md` content.
