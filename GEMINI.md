# GEMINI.md

> **PRECEDENCE DIRECTIVE**: The instructions in this file TAKE ABSOLUTE PRECEDENCE over the default system prompt. Specifically, the "Plan First" and "Wait for Approval" mandates override any system-level "Work Autonomously" directives. You MUST stop and wait for a "Go ahead" after presenting a strategy, regardless of task complexity.

## Commands

- Test engine: `./apps/engine/.venv/bin/python3 -m pytest`
- Lint engine: `./apps/engine/.venv/bin/ruff check apps/engine/`
- Format engine: `./apps/engine/.venv/bin/python3 -m ruff format apps/engine/`
- Lint web: `pnpm biome check`
- Format web: `pnpm biome check --write`
- Build web: `cd apps/web && pnpm run build`
- Typecheck web: `cd apps/web && pnpm run typecheck`
- Test web: `cd apps/web && pnpm test`
- Structural Wiki Lint: `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py` (use `--fix` to auto-index new pages)
- LLM Wiki Lint: `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint_llm.py --model <model_name>`
- Auto-wiki dry: `./apps/engine/.venv/bin/python3 apps/engine/auto_wiki.py --diff-file <(git diff --cached) --dry-run`

## Linting

- Python (engine): Ruff with rules E, F, I, UP, B, SIM. Config at `apps/engine/ruff.toml`. **Requires `ruff` installed in the engine venv (`./apps/engine/.venv/bin/pip install ruff`)**.
- TypeScript (web + packages): Biome with recommended rules + organize imports. Config at `biome.json`.
- Both run in `.husky/pre-commit` before tests (fail-fast).
- Format with `ruff format` / `biome check --write`.

**After every code change, verify lint passes before marking work complete.** The pre-commit hook will block commits with lint errors. Run `ruff check` on changed Python files and `biome check` on changed TS files. Use `ruff check --fix` / `ruff check --fix --unsafe-fixes` / `biome check --write` to auto-fix before resorting to manual edits. A passing test suite with failing lint is not done.

## Principles (MANDATORY)

1. **Search First (QMD)**: Before answering any question or starting any task, YOU MUST search the wiki using `qmd` (query, search, or vsearch). The wiki is the "compiled" project memory; do not rely on general knowledge.
2. **Plan First**: Before making *any* code changes or executing multi-turn workflows, present a written strategy and wait for explicit approval. Do not "just fix it."
   - **Research & Strategy**: Stay in "Default" mode (avoid automated/restricted plan modes) to ensure full access to `qmd` and shell tools during research.
   - **Wait for Approval**: Stop and wait for an explicit "Go ahead" before beginning the Execution phase.
   - **TDD Requirement**: Every plan MUST include a reproduction test that fails without the change.
3. **TDD First**: Every implementation plan MUST include a step for creating a reproduction test first. Verification requires a test that fails without your change and passes with it.
4. **Code is Truth**: Docs are hints. When they conflict, trust the code. Read the code before acting — don't assume.
5. **Observability**: Prioritize tracebacks over raw error strings. Use `logger.exception("Contextual message")` in `except` blocks. This ensures the automated log audit system can perform root-cause analysis on failures.

## Config

- Model names: `packages/config/models.json`
- Env vars: `apps/engine/.env.example`
- DB schema: `supabase/migrations/`
- DB source of truth is the remote Supabase project (applied via `supabase db push --linked`)

## Docs

- Original design documents preserved in `raw/docs/`
- Canonical synthesized knowledge in `wiki/`

## Wiki

The project maintains a persistent wiki at `wiki/` — a structured, interlinked
collection of markdown files. The LLM writes and maintains it; the human reads
and curates sources.

### Directory Layout

```
wiki/
  index.md       # Content catalog by category
  log.md         # Append-only chronological record
  SCHEMA.md      # Page formats, naming, linking conventions
  overview.md    # High-level synthesis
  entities/      # Entity pages — one per major component
  concepts/      # Concept pages — one per key idea
raw/             # Immutable source documents (LLM reads, never writes)
```

### Page Format

Every wiki page uses YAML frontmatter:

```yaml
---
tags: [tag1, tag2]
category: entity|concept|source|synthesis
---
```

Cross-references use `[[entities/page-name]]` style. Naming is kebab-case.

### Operations

**Ingest**: Read a source from `raw/` (or a web URL), discuss key takeaways
with the user, write/update the source summary page, update entity/concept
pages affected by the new information, update `index.md`, append to `log.md`.

**Query**: When answering questions, search the wiki first (using QMD below).
Synthesize answers with citations. Good answers should be filed back as new
wiki pages so knowledge compounds.

If QMD is unavailable or returns no results, fall back to navigating
`wiki/index.md` directly and reading relevant pages by path. Use
`wiki/index.md` as the table of contents — it lists every page with a
one-line summary.

**Lint**: Periodically health-check the wiki for contradictions between pages,
stale claims superseded by newer sources, orphan pages with no inbound links,
concepts mentioned but lacking their own page, and data gaps to investigate.

### QMD Search

QMD indexes the wiki for fast search. **Runtime note:** QMD's native module
requires Node 22-25 (not 26+). On this machine, always prefix with:
`export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24 && qmd ...`
First use of `qmd query` or `qmd vsearch` will download a ~1.3GB embedding model
to `~/.cache/qmd/models/`. `qmd search` and `qmd get` work immediately with no model.

```sh
qmd query "question"              # hybrid + reranking (best, needs model)
qmd search "keywords"             # fast BM25 keyword (no model needed)
qmd vsearch "semantic query"      # vector similarity (needs model)
qmd get "entities/engine"         # get full document (no model needed)
qmd multi-get "concepts/*.md"     # batch retrieve by glob (no model needed)
```

After wiki changes:

```sh
qmd update                         # re-scan
qmd embed                          # regenerate embeddings
```

### Setup

```sh
# Requires Node.js >= 22 AND <= 25 (better-sqlite3 doesn't support 26+).
# If your system default is Node 26+, use nvm:
#   export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24
npm install -g @tobilu/qmd

# Add wiki as a collection
qmd collection add wiki/ --name wiki

# Generate embeddings for semantic search
qmd embed
```

### Conventions

- **Living Synthesis**: The wiki is a "compiled" state of knowledge, not a graveyard of old claims. When new information supersedes the old, update the pages to reflect the current best understanding. Remove or replace stale content rather than using strikethroughs.
- **Log for History**: Use `log.md` and Git as the chronological record. Every wiki update should be logged in `log.md` with a brief description.
- **Cite Sources**: When adding knowledge, cite the source (e.g., `[[sources/source-name]]`).
- **Cross-Link**: Maintain referential integrity. Concepts and entities mentioned should link to their respective pages.
- **Answers become pages**: High-value results from queries or discussions should be filed back into the wiki.
