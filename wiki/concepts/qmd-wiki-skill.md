---
tags: [qmd, search, skill, pi, mcp, wiki, agent-workflow]
category: concept
---

# QMD Wiki Search Skill (Pi)

**QMD Wiki Search** is the Pi-runtime skill that makes QMD retrieval the mandatory first step before answering any question about this repository. It is registered at `.pi/skills/qmd-wiki/SKILL.md` and backs GEMINI.md Principle 1 (search before answering) with a concrete Pi-side workflow over the `wiki`, `git-history`, and `knowledge-db` collections.

## Why It Exists

Pi is a separate agent runtime from Antigravity/Claude Code, so it needs its own wiring to reach the same QMD index the rest of the toolchain uses. Without it, Pi answers project questions from parametric memory instead of the living wiki. The skill closes that gap and also documents the two failure modes that bite every new session: CUDA out-of-memory on embedding-backed queries, and Node 26 breaking QMD's native module.

## Runtime Wiring

Two files under `.pi/` make the skill usable:

- `.pi/APPEND_SYSTEM.md` — a symlink to `../GEMINI.md`, so Pi loads the full project instructions. `AGENTS.md` is only a pointer; the canonical mandates live in `GEMINI.md`.
- `.pi/mcp.json` — registers the `qmd` MCP server, launched through a bash login shell that activates Node 24 before `exec qmd mcp`:

```json
{
  "mcpServers": {
    "qmd": {
      "command": "bash",
      "args": [
        "-lc",
        "export NVM_DIR=\"$HOME/.nvm\"; . \"$NVM_DIR/nvm.sh\" >/dev/null 2>&1; nvm use 24 >/dev/null 2>&1; exec qmd mcp"
      ],
      "description": "QMD search over this repo's wiki, git history, and knowledge-db markdown collections"
    }
  }
}
```

The `nvm use 24` prefix is not cosmetic — QMD's native module supports Node 22–25 only, and the wrapper guarantees the MCP server never starts on an unsupported runtime. See [[concepts/mcp-setup]] for the general MCP configuration model.

## Procedure

1. **Start with QMD.** Prefer the MCP tools: `mcp__qmd__query` with `searches: [{ "type": "lex", "query": "..." }]`, `collections: ["wiki", "git-history", "knowledge-db"]`, and an `intent` stating what to find and what to avoid. Add `vec` or `hyde` subqueries only when lexical search fails and GPU memory is available.
2. **Read the page, not the snippet.** Use `mcp__qmd__get` or `mcp__qmd__multi_get` and open the full document before relying on a fact. Snippets are leads.
3. **Shell fallback** hits the same index:

   ```sh
   export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24
   qmd search "keywords" -c wiki -n 10
   qmd get "entities/engine.md"
   qmd multi-get "concepts/*.md"
   ```

4. **Fall back to the catalog.** If QMD returns nothing, open `wiki/index.md` and follow its links. After wiki edits, run `qmd update && qmd embed` under Node 24 plus `wiki_lint.py` (see [[concepts/wiki-synchronization]]).
5. **Cite the source.** When an answer depends on wiki content, cite the QMD path or docid.

## Pitfalls

- `qmd query` and `qmd vsearch` load `node-llama-cpp` on CUDA and have failed here with `cudaMalloc failed: out of memory`. Use `qmd search` (BM25) or lex-only MCP subqueries first.
- QMD's native module needs Node 22–25; Node 26+ breaks it. Prefix shell commands with `nvm use 24` — the MCP wrapper already does.
- Never answer from snippets alone; fetch the page with `get` or `multi-get`.
- `AGENTS.md` is only a pointer. The full instructions live in `GEMINI.md`, loaded into Pi through `.pi/APPEND_SYSTEM.md`.

## Verification

- `qmd ls` lists `wiki`, `git-history`, and `knowledge-db`.
- A lex QMD search returns matching paths and docids.
- Resolving `.pi/APPEND_SYSTEM.md` reaches the `GEMINI.md` content.

## Related

- [[concepts/mcp-setup]] — MCP server configuration, plugins, and schema caching
- [[concepts/wiki-synchronization]] — the re-index and lint loop after wiki edits
- [[entities/wiki-linter]] — structural validation of the wiki QMD indexes
- [[entities/agent-rules]] — project-level mandates including the search-first principle
