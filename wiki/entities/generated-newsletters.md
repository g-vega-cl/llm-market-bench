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

## Downstream Consumers & Tooling Integration

1. **Daily S&P Market Predictor**:
   - [`get_daily_market_context()`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tasks/daily_predictor.py) automatically queries the fresh morning newsletter from `generated_newsletters` via `execute_fetch_daily_newsletter_tool(session="open")` and injects the full synthesized Markdown briefing into the pre-market context block.
   - Falls back gracefully to the most recent available newsletter if the target date's morning briefing is delayed.

2. **Autonomous Portfolio LLM Trading Agents**:
   - Exposed as a canonical OpenAI/Anthropic/Gemini tool `fetch_daily_newsletter` in `core/llm/tools.py` (`DEFAULT_OPENAI_TOOLS`, `DEFAULT_ANTHROPIC_TOOLS`, `DEFAULT_GEMINI_TOOLS`).
   - Allows trading decision agents to pull morning/evening briefs dynamically.

3. **Weekly Autoresearch Meta-Agent**:
   - In `autoresearch/tools.py`, `query_past_newsletters(limit=5, session="open")` enables the prompt optimization meta-researcher to inspect past market briefs to diagnose macroeconomic regime shifts.

4. **Sequencing & Edge Dispatch**:
   - The morning newsletter generates at **9:15 AM ET**, providing a 5-minute window before the Daily S&P Predictor executes at **9:20 AM ET** (see [[entities/cron-dispatcher]]).

## UI Presentation

- **Web Route**: `/generated-newsletters` (component: `GeneratedNewslettersPage.tsx`). Synthesized ~6 minute reads.
- **Markdown Rendering**: Article body content synthesized in Markdown is rendered via a custom zero-dependency `<MarkdownContent />` component (`apps/web/src/components/ui/MarkdownContent.tsx`), formatting headings, blockquotes, lists, bold/italic inline text, and tables without third-party dependencies.

## Related

- [[concepts/ingestion]]
- [[entities/cron-dispatcher]]
- [[entities/daily-market-predictor]]
- [[entities/pipeline]]
- [[entities/autoresearch]]

