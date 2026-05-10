# AGENTS.md

## Commands
- Test engine:   `./apps/engine/venv/bin/python3 -m pytest`
- Lint engine:   `ruff check apps/engine/`
- Build web:     `cd apps/web && pnpm run build`
- Typecheck web: `cd apps/web && pnpm run typecheck`
- Test web:      `cd apps/web && pnpm test`

## Principles
- Code is truth. Docs are hints. When they conflict, trust the code.
- Read the code before acting — don't assume.
- Small, verifiable changes. Test after each.

## Config
- Model names:   `packages/config/models.json`
- Env vars:      `apps/engine/.env.example`
- DB schema:     `supabase/migrations/`
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

QMD indexes the wiki for fast search:
```sh
qmd query "question"              # hybrid + reranking (best)
qmd search "keywords"             # fast BM25 keyword
qmd vsearch "semantic query"      # vector similarity
qmd get "entities/engine"         # get full document
qmd multi-get "concepts/*.md"     # batch retrieve by glob
```

After wiki changes:
```sh
qmd update                         # re-scan
qmd embed                          # regenerate embeddings
```

### Setup

```sh
# Install QMD (requires Node.js >= 22)
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
