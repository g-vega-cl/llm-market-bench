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
```

## Page Format

Every wiki page follows this structure:

```markdown
---
tags: [tag1, tag2]
category: entity|concept|source|synthesis
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
| `category` | Yes | One of: `entity`, `concept`, `source`, `synthesis` |
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

QMD indexes the wiki for fast search:

```sh
qmd query "your question"          # hybrid search + reranking (best quality)
qmd search "keywords"              # fast BM25 keyword search
qmd vsearch "semantic query"       # vector similarity search
qmd get "path/to/page"             # retrieve full document
qmd multi-get "entities/*.md"      # batch retrieve by glob
```

After every significant wiki change, re-index:
```sh
qmd update                         # re-scan filesystem for changes
qmd embed                          # regenerate embeddings
```

## Maintenance Rules

1. **Never delete** — strike through deprecated content or mark it superseded
2. **Log every action** — append to `log.md` with `## [YYYY-MM-DD] action | Title`
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

