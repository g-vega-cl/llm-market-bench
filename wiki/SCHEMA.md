---
tags: [tag1, tag2]
category: entity|concept|source|synthesis|interaction
---

# Wiki Schema & Conventions

The LLM writes and maintains this wiki. The human curates sources and asks questions.

## Directory Layout

```
wiki/
  index.md          # Content catalog — every page listed with link + one-line summary
  log.md            # Append-only chronological record of ingests, queries, lint passes
  SCHEMA.md         # This file — conventions, page formats, linking rules
  overview.md       # High-level synthesis of the project
  entities/         # Entity pages — one per major component (engine, database, pipeline, etc.)
  concepts/         # Concept pages — one per key idea (consensus, tool enforcement, RAG, etc.)
  sources/          # Source summaries — synthesized takeaways from raw/ documents
  interactions/     # Promoted Q&A — significant discussions and answers
```

## Page Format

Every wiki page follows this structure:

```markdown
---
tags: [tag1, tag2]
category: entity|concept|source|synthesis|interaction
---

# Page Title

Brief one-paragraph summary. What is this thing and why does it matter?

## Sections

Use level-2 headings for major sections. Content is prose with examples,
diagrams, and cross-references. Keep it dense but readable.

## Related

- [[entities/engine]] — reference to another wiki page
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `tags` | Yes | Categorization tags |
| `category` | Yes | One of: `entity`, `concept`, `source`, `synthesis`, `interaction` |
| `related` | No | List of related wiki page paths |

## Cross-References

Use `[[entities/engine]]` style references between wiki pages. The LLM resolves
these when reading. The human sees them as clickable links in Obsidian.

### Naming Conventions

- **Entity pages**: `kebab-case.md` — named after the component they describe
- **Concept pages**: `kebab-case.md` — named after the concept

### Link Format

- `[[entities/engine]]` links to `wiki/entities/engine.md`
- `[[concepts/consensus]]` links to `wiki/concepts/consensus.md`

### Orphan Detection

Every page should have at least one inbound link from another page or from
`index.md`. Orphan pages are flagged during lint passes.

## QMD Search

QMD indexes the wiki for fast search. **Runtime note:** QMD's native module
requires Node 22-25 (not 26+). On this machine, always prefix with:
  `export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24 && qmd ...`

First use of `qmd query` or `qmd vsearch` will download a ~1.3GB embedding model
to `~/.cache/qmd/models/`. `qmd search` and `qmd get` work immediately with no model.

```sh
qmd query "your question"          # hybrid search + reranking (best quality, needs model)
qmd search "keywords"              # fast BM25 keyword search (no model needed)
qmd vsearch "semantic query"       # vector similarity search (needs model)
qmd get "path/to/page"             # retrieve full document (no model needed)
qmd multi-get "entities/*.md"      # batch retrieve by glob (no model needed)
```

After every significant wiki change, re-index:
```sh
qmd update                         # re-scan filesystem for changes
qmd embed                          # regenerate embeddings
```

## Maintenance Rules

1. **Refine Synthesis** — Keep pages sharp and current. Replace or remove stale/superseded content to maintain a clean "current best" understanding. Do not use strikethroughs for old content; rely on Git and `log.md` for history.
2. **Log every action** — append to `log.md` with `## [YYYY-MM-DD] action | Title`. The file is automatically rotated into `wiki/log/YYYY-MM.md` buckets when it exceeds 30KB.
3. **Answers become pages** — good query answers get filed back into the wiki
4. **Lint weekly** — check for contradictions, orphans, stale claims, gaps

## Automated Lint

The wiki has two layers of automated quality checks:

- **Structural lint** (`apps/engine/wiki_lint.py`) — runs on every commit via
  pre-commit hook. Checks: frontmatter completeness, broken `[[links]]`, orphan
  pages, index coverage gaps. Runs in ~20ms with no API cost.

- **LLM lint** (`apps/engine/wiki_lint_llm.py`) — runs weekly via GitHub Actions
  (Saturday 10:00 ET). Sends all wiki pages to DeepSeek via OpenRouter to check
  for contradictions, stale claims, missing concept pages, data gaps, weak
  cross-references, and thin pages. Posts findings as a labeled GitHub Issue.
  Can also be triggered manually:
  ```sh
  gh workflow run wiki-lint.yml -f model="any-openrouter-model"
  ```

## Installation (for reference)

```sh
# Requires Node.js >= 24 AND <= 25 (better-sqlite3 doesn't support 26+).
# If your system default is Node 26+, use nvm:
#   export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24
npm install -g @tobilu/qmd

# Add wiki as a collection
qmd add wiki
```
