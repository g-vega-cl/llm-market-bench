---
tags: [newsletter, generation, pipeline, ai]
category: entity
---

# Generated Newsletters

Auto-generated daily market newsletters produced by the engine. The newsletter generator runs on a cron schedule (see [[entities/cron-dispatcher]]) and creates a digest of top market events, LLM sentiment, and portfolio updates.

## Generation Process

1. **Trigger**: GitHub Actions workflow `.github/workflows/generate-newsletter.yml`
2. **Ingestion**: Calls `ingest_newsletters()` to fetch the latest newsletters from email sources.
3. **Query**: Fetches newsletter snapshots from the **last 12 hours** using the `date` field (previously `ingested_at`). The 12-hour window is a rolling window from the current Eastern Time.
4. **LLM**: Uses DeepSeek V4 Flash to summarize the most impactful events into a structured newsletter (title, sections, key events, source attribution).
5. **Storage**: The generated newsletter is inserted into the `newsletter_snapshots` table with a unique ID.

## Configuration

- **Secrets**: Requires `DEEPSEEK_API_KEY`, `GEMINI_API_KEY` (for other workflow steps), `SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and Gmail credentials.
- **Session**: Passes a `session` parameter ("open" or "close") to differentiate morning/evening editions.

## Related

- [[concepts/ingestion]]
- [[entities/cron-dispatcher]]
- [[entities/pipeline]]
