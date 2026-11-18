---
tags: [knowledge-db, qmd, sync, documentation, search]
category: entity
---

# Knowledge DB Sync

An automated synchronization engine that exports curated engineering patterns, articles, and newsletters from the external Supabase `knowledge_emails` and `knowledge_documents` tables into local, gitignored Markdown files in `knowledge-db/`, and indexes them as a federated QMD collection.

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

5. **Long-Form Article Mirror (`sync_knowledge_documents.py`)**:
   - Exports the `knowledge_documents` table (parsed GreatFrontEnd system-design articles) to `knowledge-db/greatfrontend/<slug>.md`, one file per document, with `title`, `url`, `source`, `slug`, `access`, `published_at`, `content_hash` frontmatter and the stored Markdown body verbatim — QMD chunks the file on its own headings.
   - Rewrites a file only when its `content_hash` changes, so a re-parse upstream propagates without clearing the mirror. When the producer supplies no hash, it falls back to a SHA-256 of the Markdown body.
   - Requires a service/secret key: `knowledge_documents` has no anon grant, so an anon key answers with zero rows rather than an error. `_resolve_key()` therefore prefers `SUPABASE_SECRET_KEY` over `MISC_SUPABASE_KEY`/`SUPABASE_KEY`/`SUPABASE_SERVICE_ROLE_KEY`/`VITE_SUPABASE_ANON_KEY`, and the export prints a warning when zero rows come back.
   - Disable with `--skip-documents` when only the email corpus is wanted.
   - `sync_knowledge_db.py` imports `fetch_and_export_documents` from this module (with a script-mode fallback import) and runs it as Step 3b, before the QMD refresh. The QMD index is refreshed when either emails or documents were written.

6. **Credential Resolution (`get_supabase_client` / `_resolve_key`)**:
   - Loads **every** candidate env file (`apps/engine/.env`, `../knowledge-db/.env`, repo-root `.env`) unconditionally — `dotenv` never overrides an already-set variable — so a secret key living in `../knowledge-db/.env` is visible even when `apps/engine/.env` already supplied an anon key.
   - URL resolves from `MISC_SUPABASE_URL` → `SUPABASE_URL` → `VITE_SUPABASE_URL`; the key resolves via `_resolve_key()` (service-level key wins over anon).

## Usage

### Run Sync

```bash
# Via pnpm script
pnpm knowledge:sync

# Or directly via Python venv
./apps/engine/.venv/bin/python3 apps/engine/sync_knowledge_db.py

# Dry run (test connection and see counts without writing files)
./apps/engine/.venv/bin/python3 apps/engine/sync_knowledge_db.py --dry-run --limit 10

# Emails only — leave knowledge_documents articles untouched
./apps/engine/.venv/bin/python3 apps/engine/sync_knowledge_db.py --skip-documents
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

# Long-form articles mirror under greatfrontend/
qmd search -c knowledge-db "preload carousel images"
qmd get "knowledge-db/greatfrontend/image-carousel.md:1" -l 40
```

## Related

- [[entities/git-history]] — Git history export and QMD indexing
- [[entities/wiki-linter]] — Structural wiki verification
- [[concepts/mcp-setup]] — Model Context Protocol and external knowledge retrieval
