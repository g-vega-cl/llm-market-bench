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
5. **Live Economic Releases & Macro Surprises**: Queries FMP via `get_today_economic_releases_summary()` for 8:30 AM ET and morning macroeconomic prints (CPI, Core CPI, PPI, Jobs/Payrolls, Retail Sales, Unemployment, GDP) with actual vs consensus surprises, prior values, and release status (RELEASED vs PENDING), cached for 30 minutes.
6. **Options Derivatives & Volatility Structure**: Queries options positioning and volatility dynamics via `get_newsletter_options_context()` including cross-asset macro options sentiment table covering `SPY`, `QQQ`, `IWM`, and `GLD` (Put/Call ratios, Max Pain, 25-delta skew via `execute_get_macro_options_sentiment_tool`), SPY options volatility surface and 1-sigma daily move cone (via `execute_options_vol_surface_tool`), VIX term structure and curve dynamics (via `execute_get_volatility_index_details_tool`), and US Treasury yield curve slope & flow regime (via `execute_yield_curve_regime_tool`).
7. **Foreign Exchange & Dollar Dynamics (FX)**: Queries live market quotes via `get_newsletter_fx_context()` covering the US Dollar Index Bullish Fund (`UUP` / DXY proxy) and core major currency pairs (`EURUSD`, `USDJPY`), supplemented by FRED's Nominal Broad U.S. Dollar Index (`DTWEXBGS`), ensuring grounded spot FX rates and overnight moves for macro cross-asset synthesis.
8. **LLM**: Uses DeepSeek V4 Flash to summarize and synthesize the most impactful events, economic data, options positioning, and currency dynamics into a comprehensive 6-minute newsletter (~1,200–1,500 words, ~6 min read) featuring:
   - `### 🌐 The Macro & Cross-Asset Narrative`
   - `### 🔬 Sector & Earnings Spotlight`
   - `### 📈 Market Internals, Sentiment & Flows`
   - `### 💡 Trade Ideas & Scenarios to Watch`
   - `### 🗓️ The Catalyst Radar & Key Levels`
9. **Storage**: The generated newsletter is inserted into the `generated_newsletters` table with a unique ID and `read_time_minutes` (default 6).

## Downstream Consumers & Tooling Integration

1. **Daily S&P Market Predictor**:
   - [`get_daily_market_context()`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/tasks/daily_predictor.py) automatically queries dual newsletters from `generated_newsletters`:
     - **Prior Close Briefing**: `execute_fetch_daily_newsletter_tool(session="close", include_full_content=False)` injects the previous session's closing headline, executive summary, and key takeaways without token bloat (or full content if `include_full_prior_close=True`).
     - **Today's Open Briefing**: `execute_fetch_daily_newsletter_tool(session="open", include_full_content=True)` injects the full synthesized Markdown morning briefing into the pre-market context block.
   - Falls back gracefully to the most recent available newsletter if the target date's morning briefing is delayed.

2. **Autonomous Portfolio LLM Trading Agents**:
   - Exposed as a canonical OpenAI/Anthropic/Gemini tool `fetch_daily_newsletter` in `core/llm/tools.py` (`DEFAULT_OPENAI_TOOLS`, `DEFAULT_ANTHROPIC_TOOLS`, `DEFAULT_GEMINI_TOOLS`).
   - Allows trading decision agents to pull morning/evening briefs dynamically.

3. **Weekly Autoresearch Meta-Agent**:
   - In `autoresearch/tools.py`, `query_past_newsletters(limit=5, session="open", include_full_content=False)` enables the prompt optimization meta-researcher to inspect past market briefs (either executive summaries or full Markdown articles via `include_full_content=True`) to diagnose macroeconomic regime shifts.

4. **Sequencing & Chained Dispatch**:
   - The morning newsletter generates at **9:12 AM ET** via Cloudflare Worker edge dispatch (see [[entities/cron-dispatcher]]).
   - Upon completion, `generate-newsletter.yml` automatically triggers `daily-predictor.yml` (`session: open` triggers `daily-predictor` and `session: close` triggers `evaluate-daily-predictions`), ensuring the predictor runs immediately after newsletter synthesis without race conditions.
   - **Auto-Session & Cutoff Safety**: Manual workflow dispatch defaults to `session: auto`, which dynamically resolves to `open` between 13:00 and 15:00 UTC (9:00 - 11:00 AM EDT) and `close` outside that window. The workflow timeout is 15 minutes. Downstream predictor chaining enforces a strict pre-market cutoff ($< 13:30$ UTC), ensuring an `open` manual dispatch outside morning hours will never trigger pre-market predictions after market open.

## UI Presentation

- **Web Route**: `/generated-newsletters` (component: `GeneratedNewslettersPage.tsx`). Synthesized ~6 minute reads.
- **Markdown Rendering**: Article body content synthesized in Markdown is rendered via a custom zero-dependency `<MarkdownContent />` component (`apps/web/src/components/ui/MarkdownContent.tsx`), formatting headings, blockquotes, lists, bold/italic inline text, and tables without third-party dependencies.

## Related

- [[concepts/ingestion]]
- [[entities/cron-dispatcher]]
- [[entities/daily-market-predictor]]
- [[entities/pipeline]]
- [[entities/autoresearch]]

