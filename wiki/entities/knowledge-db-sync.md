---
tags: [knowledge-db, qmd, sync, documentation, search]
category: entity
---

# Knowledge DB Sync

An automated synchronization engine that exports curated engineering patterns, articles, and newsletters from the external Supabase `knowledge_emails` table into local, gitignored Markdown files in `knowledge-db/`, and indexes them as a federated QMD collection.

## Overview

The `knowledge-db` repository (`../knowledge-db`) ingests newsletters and technical articles into Supabase (`misc` database) with metadata and vector embeddings. To make this information available locally, offline, and at sub-second retrieval speeds during feature design and coding, `sync_knowledge_db.py` bridges Supabase to the project's local QMD setup.

## Architecture

```
External Supabase (knowledge_emails)
            │
            ▼ (apps/engine/sync_knowledge_db.py)
   knowledge-db/*.md (Gitignored local cache)
            │
            ▼ (qmd collection add / update / embed)
   QMD SQLite Index (~/.cache/qmd/index.sqlite)
            │
            ▼
   qmd query -c knowledge-db "query" / qmd query "query"
```

### Components

1. **Defensive Git Boundary (`ensure_gitignore`)**:
   Automatically verifies that `knowledge-db/` is listed in `.gitignore` before writing files to prevent external source documents from being checked into Git or pushed to GitHub.

2. **Sanitization & Markdown Formatting (`format_article_markdown`)**:
   - Strips `<script>`, `<style>`, and tracking artifacts from email bodies.
   - Converts HTML linebreaks and paragraphs into clean Markdown.
   - Unescapes HTML entities.
   - Attaches YAML frontmatter (`title`, `sender`, `date`, `gmail_id`, `tags: [knowledge-db, architecture]`).

3. **Incremental & Idempotent Sync (`fetch_and_export_knowledge`)**:
   - Paginates through Supabase records in 200-row batches via `.range()`.
   - Checks existing document IDs (`YYYY-MM-DD_slug--<short_id>.md`) on disk to skip already exported records.

4. **QMD Collection Automation (`update_qmd_index`)**:
   - Registers `knowledge-db/` under the `knowledge-db` collection name via `qmd collection add`.
   - Triggers `qmd update` (BM25 + AST chunking) and `qmd embed` (vector embeddings).

## Usage

### Run Sync

```bash
# Via pnpm script
pnpm knowledge:sync

# Or directly via Python venv
./apps/engine/.venv/bin/python3 apps/engine/sync_knowledge_db.py

# Dry run (test connection and see counts without writing files)
./apps/engine/.venv/bin/python3 apps/engine/sync_knowledge_db.py --dry-run --limit 10
```

### Search Knowledge Base via QMD

```bash
# Query across all collections (wiki + git-history + knowledge-db)
qmd query "how to design circuit breaker with exponential backoff"

# Targeted search in knowledge-db only
qmd query -c knowledge-db "tanstack query state hydration"
qmd search -c knowledge-db "HTTP/3 QUIC"

# Inspect specific document
qmd get "knowledge-db/2026-02-01_ep200-http-2-over-tcp--19c14ea5cd88.md:1" -l 40
```

## Related

- [[entities/git-history]] — Git history export and QMD indexing
- [[entities/wiki-linter]] — Structural wiki verification
- [[concepts/mcp-setup]] — Model Context Protocol and external knowledge retrieval
