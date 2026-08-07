---
tags: [newsletters, deepseek, synthesis, web-app, cron-dispatcher]
category: entity
---

# Generated Newsletters

The **Generated Newsletters** feature synthesizes daily ingested financial newsletter snapshots into concise, 1–2 minute read market intelligence briefings twice every day (at market open 09:00 ET and market close 17:00 ET).

## Pipeline & Architecture

1. **Trigger**: Cloudflare Worker Cron Dispatcher ([`apps/cron-dispatcher`](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/cron-dispatcher)) triggers GitHub Workflow `generate-newsletter.yml` at 13:00 UTC (09:00 ET, open) and 21:00 UTC (17:00 ET, close).
2. **Engine Ingestion & Generation**: `apps/engine/tasks/newsletter_generator.py` runs Gmail ingestion (`ingest_newsletters()`) to idempotently upsert fresh email snapshots into Supabase, queries a rolling 24-hour window of `newsletter_snapshots`, and passes them to **DeepSeek V4 Flash** (`deepseek-v4-flash`).
3. **Structured Response**:
   - `title`: Punchy headline
   - `summary`: Executive 1–2 sentence summary
   - `bullet_points`: 2–4 key takeaway bullet points
   - `content`: Formatted Markdown body (~250–400 words, ~1–2 min read)
   - `formatted_time`: Exact creation timestamp (e.g. `09:00 ET` / `17:00 ET`)
4. **Database Storage**: Output is inserted into `generated_newsletters` table in Supabase (requires explicit PostgREST `GRANT` statements for Data API exposure).
5. **Web UI**: Accessible at route `/generated-newsletters` linked directly from the "AI News Synthesis" card on `/today`.


## Database Schema (`generated_newsletters`)

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Primary key |
| `title` | TEXT | Newsletter title |
| `summary` | TEXT | Executive summary |
| `content` | TEXT | Full Markdown body |
| `bullet_points` | JSONB | List of key bullet points |
| `session` | TEXT | `'open'` or `'close'` |
| `read_time_minutes` | INTEGER | Estimated read time (default 2) |
| `source_count` | INTEGER | Number of ingested newsletters summarized |
| `formatted_time` | TEXT | Creation time string (e.g. `09:00 ET`) |
| `created_at` | TIMESTAMPTZ | Creation timestamp |

## Related

- [[entities/cron-dispatcher]] — Cloudflare Worker cron dispatcher
- [[concepts/ingestion]] — Ingest stream and snapshotting
- [[entities/web-app]] — Web dashboard
