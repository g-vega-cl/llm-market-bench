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
4. **Macroeconomic Pulse**: Queries [[concepts/macroeconomic-data-fred]] via `get_curated_macro_dashboard()` for real-time benchmark interest rates, yield curve spreads (10Y-2Y), CPI/PCE inflation, labor metrics, and credit spreads.
5. **LLM**: Uses DeepSeek V4 Flash to summarize and synthesize the most impactful events and economic data into a comprehensive 6-minute newsletter (~1,200–1,500 words, ~6 min read) featuring:
   - `### 🌐 The Macro & Cross-Asset Narrative`
   - `### 🔬 Sector & Earnings Spotlight`
   - `### 📈 Market Internals, Sentiment & Flows`
   - `### 💡 Trade Ideas & Scenarios to Watch`
   - `### 🗓️ The Catalyst Radar & Key Levels`
6. **Storage**: The generated newsletter is inserted into the `generated_newsletters` table with a unique ID and `read_time_minutes` (default 6).

## UI Presentation

- **Web Route**: `/generated-newsletters` (component: `GeneratedNewslettersPage.tsx`). Synthesized ~6 minute reads.
- **Markdown Rendering**: Article body content synthesized in Markdown is rendered via a custom zero-dependency `<MarkdownContent />` component (`apps/web/src/components/ui/MarkdownContent.tsx`), formatting headings, blockquotes, lists, bold/italic inline text, and tables without third-party dependencies.

## Related

- [[concepts/ingestion]]
- [[entities/cron-dispatcher]]
- [[entities/pipeline]]

