---
tags: [company, research, dossier, newsletter, luna, entity]
category: entity
---

# Company Research Reports & Dossiers

The Company Research system extracts individual stocks and sector benchmark ETFs spotlighted in Benchify's daily market briefings (`[[entities/generated-newsletters]]`), conducts multi-dimensional quantitative and qualitative deep dives, and stores structured investment dossiers in PostgreSQL (`company_research_reports` and `newsletter_company_mentions`). Users can search, explore, and inspect comprehensive intelligence on any covered company via the `/companies` directory and `/companies/$ticker` dossier hub.

## Pipeline & Architecture

1. **Extraction & Normalization** (`apps/engine/tasks/ticker_extractor.py`):
   - Consumes the structured `mentioned_companies` list emitted by the newsletter generator (`GeneratedNewsletterOutput.mentioned_companies`), and falls back to scanning the newsletter body text when no structured mentions are present.
   - `CompanyMention` (Pydantic model) carries `ticker`, `company_name`, `sector`, `is_sector_etf`, `entity_type` (`stock`/`etf`), and `context_snippet`.
   - `normalize_ticker` strips whitespace and `$` prefixes, uppercases, converts `-` to `.` (e.g. `BRK-B` → `BRK.B`), and resolves company-name aliases via `ALIAS_MAP` (`Google`/`Alphabet` → `GOOGL`, `Meta Platforms`/`Facebook` → `META`, `Taiwan Semiconductor`/`TSMC` → `TSM`, etc.).
   - `normalize_sector_to_etf` maps sector phrases to benchmark ETFs via `SECTOR_ETF_MAP` (e.g. `Semiconductors`/`Chips` → `SMH`, `Cybersecurity` → `CIBR`, `Software`/`SaaS`/`Cloud` → `IGV`, `Energy`/`Oil` → `XLE`, `Financials`/`Banks` → `XLF`, `Biotech`/`Pharma` → `XBI`, `Defense`/`Aerospace` → `ITA`). Sector returns are flagged `is_sector_etf=True`.
   - **Text fallback**: `extract_and_deduplicate_mentions` scans for `$TICKER` cashtags and named parentheticals (`Apple (AAPL)`), applies `SECTOR_TEXT_PATTERNS` for explicit sector phrases, and filters out `FINANCIAL_ACRONYM_BLACKLIST` tokens (`EPS`, `YOY`, `PE`, `EV`, `TAM`, `AI`, `CEO`, `ETF`, `VIX`, `FED`, `CPI`, …) so headline acronyms and words like "blue-chip" or "central bank" never become false tickers.
   - All targets are deduplicated per run into a unique set — each ticker symbol appears at most once.

2. **Smart TTL Deduplication** (`apps/engine/tasks/research_newsletter_tickers.py`):
   - `research_single_target` checks the latest `company_research_reports` row for the ticker. When an existing dossier is younger than `TTL_SKIP_HOURS` (24 hours), heavy LLM re-generation is skipped entirely: the new newsletter mention is linked to the existing report in `newsletter_company_mentions` and the fresh row is returned.
   - `force_refresh=True` bypasses the TTL check and always regenerates a full deep dive.

3. **Multi-Dimensional Context Assembly** (`gather_target_context`):
   - Spot price and session-anchored quote via `MarketDataManager.get_reference_quote` (respecting `session` and `target_date`).
   - Fundamental valuation multiples, DCF, and balance-sheet metrics via `execute_key_metrics_tool` (`apps/engine/tools/valuation.py`).
   - Economic moat and capital allocation scorecard via `execute_call_warren_buffett_tool` (`apps/engine/tools/analyst_personas.py`) for single stocks; sector fundamentals via `execute_sector_fundamentals_tool` for ETF benchmarks.
   - Options volatility surface, IV/RV ratios, and put/call skew via `execute_get_options_sentiment_tool` (`apps/engine/tools/technicals_options.py`).
   - Every fetch is individually wrapped — a failing tool is logged at debug level and simply omitted, so one unavailable provider never aborts the dossier.

4. **Deep-Dive Synthesis (OpenAI Luna with Thinking)**:
   - Invokes OpenAI `gpt-5.6-luna` (`OPENAI_MODEL`) using Instructor with `reasoning_effort="medium"` and `response_model=CompanyResearchDossierOutput`.
   - Produces structured output:
     - Definitive Verdict (`bullish`, `bearish`, or `neutral`).
     - Conviction Score (1-100, clamped server-side) and Risk/Reward ratio (rounded, clamped 0.1–99.0).
     - Target Time Horizon (e.g. `3-6 months`).
     - Warren Buffett Moat Scorecard (`buffett_moat_analysis`: moat rating, pricing power, capital allocation, rationale).
     - Valuation summary and Options volatility summary.
     - Catalyst context (the briefing event that prompted the research).
     - 3-5 concrete falsification triggers that would invalidate the thesis.
     - Full Markdown-formatted research dossier (`full_report_markdown`).

5. **Persistence & Data Model**:
   - `company_research_reports`: historical ledger of timestamped dossiers with a unique constraint on `(ticker, date, session)` for idempotent upserts. Stores `verdict`, `conviction_score`, `risk_reward_score`, `target_horizon`, `spot_price_at_report`, `forward_5d_return`/`forward_20d_return`, `valuation_summary`, `buffett_moat_analysis` (JSONB), `options_sentiment_summary`, `catalyst_context`, `falsification_triggers` (JSONB), and `full_report_markdown`.
   - `newsletter_company_mentions`: junction table linking daily newsletters (`generated_newsletters`) to research reports with a unique constraint on `(newsletter_id, ticker)`, enabling N:N deduplication and mention counts.
   - Both tables enable RLS with public `SELECT` and `service_role` full access, plus explicit `GRANT SELECT` to `anon`/`authenticated` per [[concepts/supabase-grant-convention]].

6. **Dispatch & Concurrency**:
   - `generate_daily_newsletter` calls `_dispatch_newsletter_research` after the newsletter is persisted. It calls `research_newsletter_targets`, passing `raw_mentions=output.mentioned_companies`, `newsletter_id`, `text_fallback=output.content`, and `target_date`. Errors are caught and logged as warnings so research failures never break newsletter generation.
   - `research_newsletter_targets` runs candidates under an `asyncio.Semaphore(3)` and gathers them with `asyncio.gather`, so multiple targets research concurrently without saturating providers. A single target failure is logged and dropped from the result set rather than aborting the batch.

## CLI Usage

Run on-demand company research from the terminal via the `research-company` command (`COMMAND_RESEARCH_COMPANY`, handled by `handle_research_company` in `apps/engine/cli/predictions.py`):

```bash
# Research an individual stock or sector
./apps/engine/.venv/bin/python3 apps/engine/main.py research-company --ticker NVDA

# Force refresh ignoring the smart TTL cache
./apps/engine/.venv/bin/python3 apps/engine/main.py research-company --ticker SMH --force
```

The command builds a `CompanyMention` from `--ticker` (default `NVDA`), optional `--name`/`--sector`, and calls `research_single_target` with `session="on_demand"`, then prints the verdict and conviction score. See [[entities/cli]].

## Web Experience

- `/companies` (`CompaniesPage.tsx` / `fetch-companies.ts`): searchable directory (by ticker, name, or sector), verdict filter pills (`all`/`bullish`/`neutral`/`bearish`), and equal-height cards showing ticker, company name, sector, latest verdict + conviction, spot price, and mention count. The list fetch projects only lean scalar columns (never the heavy markdown blob) per [[concepts/zero-frontend-compute]].
- `/companies/$ticker` (`CompanyDossierPage.tsx` / `fetch-company-dossier.ts`): comprehensive dossier with verdict banner, moat / valuation / options cards, an amber thesis falsification panel, the full Markdown dossier rendered via `MarkdownContent`, and a historical research timeline switcher across past reports.
- Clickable links from `/generated-newsletters` ("Explore Company Dossiers →") and `/lab` route directly to the company explorer.

## Migration

`supabase/migrations/20261110120000_create_company_research_reports.sql` creates both tables, indexes (`ticker`, `date DESC`, `verdict`, `newsletter_id`), RLS policies, and grants. See [[entities/database]].

## Related

- [[entities/generated-newsletters]] — upstream producer of spotlighted company mentions
- [[entities/engine]] — Python data engine that hosts the research task
- [[entities/cli]] — the `research-company` command
- [[entities/database]] — `company_research_reports` and `newsletter_company_mentions` tables
- [[entities/web-app]] — the `/companies` and `/companies/$ticker` routes
- [[concepts/ingestion]] — newsletter ingestion feeding the extractor
- [[concepts/zero-frontend-compute]] — lean web read path for the directory
