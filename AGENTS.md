# AGENTS.md

## Commands

- Test engine: `./apps/engine/venv/bin/python3 -m pytest`
- Lint engine: `./apps/engine/venv/bin/ruff check apps/engine/`
- Format engine: `./apps/engine/venv/bin/ruff format apps/engine/`
- Lint web: `pnpm biome check`
- Format web: `pnpm biome check --write`
- Build web: `cd apps/web && pnpm run build`
- Typecheck web: `cd apps/web && pnpm run typecheck`
- Test web: `cd apps/web && pnpm test`
- Auto-wiki dry: `./apps/engine/venv/bin/python3 apps/engine/auto_wiki.py --diff-file <(git diff --cached) --dry-run`

## Linting

- Python (engine): Ruff with rules E, F, I, UP, B, SIM. Config at `apps/engine/ruff.toml`.
- TypeScript (web + packages): Biome with recommended rules + organize imports. Config at `biome.json`.
- Both run in `.husky/pre-commit` before tests (fail-fast).
- Format with `ruff format` / `biome check --write`.

**After every code change, verify lint passes before marking work complete.** The pre-commit hook will block commits with lint errors. Run `ruff check` on changed Python files and `biome check` on changed TS files. Use `ruff check --fix` / `ruff check --fix --unsafe-fixes` / `biome check --write` to auto-fix before resorting to manual edits. A passing test suite with failing lint is not done.

## Principles

- Code is truth. Docs are hints. When they conflict, trust the code.
- Read the code before acting — don't assume.
- **Plan & TDD First:** Before making any changes, perform research and present a written strategy for explicit approval. All implementation plans MUST include a step for creating reproduction tests first.
- Small, verifiable changes. Use Test Driven Development (TDD).
- **Observability:** Prioritize tracebacks over raw error strings. Use `logger.exception("Contextual message")` in `except` blocks. This ensures the automated log audit system can perform root-cause analysis on failures.

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

- Never delete content from wiki — strike through or mark superseded
- Log every action in `log.md` with `## [YYYY-MM-DD] action | Title`
- Answers that add value get filed back as wiki pages
- New knowledge comes from `raw/` ingest or direct wiki editing
