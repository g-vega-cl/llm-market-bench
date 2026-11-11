---
tags: [newsletter, generation, deepseek, backfill, entity]
category: entity
---

# Generated Newsletters

The newsletter generator (`apps/engine/tasks/newsletter_generator.py`) synthesizes ingested daily newsletters, FRED macro indicators, options positioning, and live economic releases into a formatted market briefing using DeepSeek V4 Flash. It runs twice daily — a Morning Market Open Briefing (9:12 AM ET) and an Evening Market Close Briefing (17:00 ET) — and stores the result in the `generated_newsletters` table.

## Pipeline

1. **Ingestion** — pulls fresh newsletters from Gmail (`ingest_newsletters`) and upserts them into `newsletter_snapshots`. Skipped for historical/backfill runs.
2. **Snapshot query** — selects snapshots published within the past 12 hours (`date >= since_iso`). For historical runs an upper bound (`date <= now_et + 15min`) is also applied so only snapshots available at the target time are used.
3. **Context assembly** — gathers macro dashboard, economic releases, options sentiment/volatility surface, FX context, and multi-horizon reference matrices (`apps/engine/analytics/market_reference.py`). Multi-horizon anchors provide tactical (20d), intermediate (60d), and structural (52w) percentiles, moving averages (20/50/200-DMA), realized volatility regimes, and Z-scores for macro core assets (`SPY`, `QQQ`, `DIA`, `IWM`, `UUP`, `EURUSD`, `USDJPY`, `TLT`, `GLD`, `USO`) and mentioned single stocks. Context helpers tolerate `Error` / `No options` / `No macro options` / unavailable prefixes by omitting those sections.
4. **Synthesis** — `_call_deepseek_flash` produces a `GeneratedNewsletterOutput` (title, summary, bullet points, content, read time, and `mentioned_companies`). The date string shown to the model is derived from the run's effective timestamp.
5. **Persistence** — inserts the record into `generated_newsletters`.
6. **Downstream research dispatch** — after a successful insert, `_dispatch_newsletter_research` forwards the briefing's `mentioned_companies` (plus the full body as a text fallback) to the company research pipeline (see [[entities/company-research-reports]]).

## Spotlighted Companies (`mentioned_companies`)

`GeneratedNewsletterOutput` carries an optional `mentioned_companies: list[dict]` field (default empty). The model is instructed to list the key single stocks or sectors spotlighted in the briefing, each as `{"ticker": "NVDA", "company_name": "NVIDIA", "sector": "Semiconductors"}`.

After the newsletter row is stored, `_dispatch_newsletter_research(output, session, newsletter_id, sb, target_date, await_research=True)` calls `tasks.research_newsletter_tickers.research_newsletter_targets`, passing:
- `raw_mentions=output.mentioned_companies`
- `session`
- `newsletter_id` (the persisted `generated_newsletters.id`)
- `text_fallback=output.content` (so cashtags and sector phrases can still be recovered when the structured list is empty)
- `target_date`

Any exception during dispatch is caught and logged as a warning, so research failures never break newsletter generation. The `generate_daily_newsletter` signature exposes two flags — `dispatch_research` (default `True`) and `await_research` (default `True`); when `await_research=False` the research is scheduled with `asyncio.create_task` and the newsletter returns immediately.

## Session-Aware Reference Quotes

The generator passes its `session` (`"open"` or `"close"`) into `get_newsletter_reference_context(..., session=session)`, which resolves quotes through `MarketDataManager.get_reference_quote(ticker, session=session, history=..., target_date=...)`. For the evening close briefing this anchors every index level and 1D move to the official regular-session close versus the prior trading day's close, rather than an after-hours tick.

`get_newsletter_fx_context(mdm=None, session="close")` uses the same resolution: it prefers `manager.get_reference_quote(ticker, session=session)` and falls back to `manager.get_premarket_quote(ticker)` when the method is absent. `generate_daily_newsletter` forwards its own `session` into the FX context call, so the UUP / EURUSD / USDJPY levels in the evening briefing are anchored to the regular-session close rather than a post-market tick.

The DeepSeek Flash system prompt carries a matching instruction: for the Evening Market Close Briefing, all equity index closing commentary (`SPY`, `QQQ`, `DIA`, `IWM`) must strictly reflect the official closing prices and 1D percentage moves from the Official Multi-Horizon Reference Matrix, never outdated pre-market or prior-session index figures found in morning newsletter text.

## Deterministic / Backfill Generation

`generate_daily_newsletter(session, sb_client, target_date)` accepts an optional `target_date` (`'YYYY-MM-DD'`). When supplied:

- The effective timestamp is pinned to the target date at the session's scheduled time (09:12 ET for `open`, 17:01 ET for `close`), so `created_at` and the prompt date string are deterministic.
- Gmail ingestion is skipped when the target date is in the past (`is_historical`).
- The snapshot query is bounded above so future-dated snapshots are excluded.
- The reference-quote layer receives the same `target_date`, so session prices and prior closes are derived from bars at or before that date and the live quote is ignored.

This enables reproducible backfills and CI-friendly generation without depending on wall-clock time. The CLI exposes it via `handle_generate_newsletter` (`--target-date`).

## Failure Behavior

If the database insert fails, the generator logs the exception and raises `RuntimeError` rather than returning the unsaved record. This ensures CI and callers surface persistence failures (e.g. Cloudflare challenge errors) instead of silently succeeding.

## Web Experience & Research Embedding

The web client (`apps/web/src/features/generated-newsletters/pages/GeneratedNewslettersPage.tsx`) presents both morning and evening briefings. When spotlighted company research dossiers are linked to a newsletter (`newsletter_company_mentions` junction table), `fetchGeneratedNewsletters` fetches the reports and renders an in-flow **Spotlighted Company & Sector Research** island between Key Takeaways and the Narrative Markdown body. Each card presents the ticker, sector, verdict, conviction score, spot price at report, catalyst snippet, and a direct link to the full institutional dossier at `/companies/$ticker`.

## Related

- [[entities/company-research-reports]]
- [[entities/pipeline]]
- [[entities/engine]]
- [[entities/market-data]]
- [[concepts/multi-horizon-reference]]
- [[concepts/ingestion]]
- [[concepts/backfilled-trades]]
- [[entities/fetch-daily-newsletter-tool]]
