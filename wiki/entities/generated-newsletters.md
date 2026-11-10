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
4. **Synthesis** — `_call_deepseek_flash` produces a `GeneratedNewsletterOutput` (title, summary, bullet points, content, read time). The date string shown to the model is derived from the run's effective timestamp.
5. **Persistence** — inserts the record into `generated_newsletters`.

## Session-Aware Reference Quotes

The generator passes its `session` (`"open"` or `"close"`) into `get_newsletter_reference_context(..., session=session)`, which resolves quotes through `MarketDataManager.get_reference_quote(ticker, session=session)`. For the evening close briefing this anchors every index level and 1D move to the official regular-session close versus the prior trading day's close, rather than an after-hours tick.

`get_newsletter_fx_context` uses the same resolution: it prefers `manager.get_reference_quote` and falls back to `manager.get_premarket_quote` when the method is absent (including bare `unittest.mock.NonCallableMock` managers that have not configured `get_reference_quote`).

The DeepSeek Flash system prompt carries a matching instruction: for the Evening Market Close Briefing, all equity index closing commentary (`SPY`, `QQQ`, `DIA`, `IWM`) must strictly reflect the official closing prices and 1D percentage moves from the Official Multi-Horizon Reference Matrix, never outdated pre-market or prior-session index figures found in morning newsletter text.

## Deterministic / Backfill Generation

`generate_daily_newsletter(session, sb_client, target_date)` accepts an optional `target_date` (`'YYYY-MM-DD'`). When supplied:

- The effective timestamp is pinned to the target date at the session's scheduled time (09:12 ET for `open`, 17:01 ET for `close`), so `created_at` and the prompt date string are deterministic.
- Gmail ingestion is skipped when the target date is in the past (`is_historical`).
- The snapshot query is bounded above so future-dated snapshots are excluded.

This enables reproducible backfills and CI-friendly generation without depending on wall-clock time. The CLI exposes it via `handle_generate_newsletter` (`--target-date`).

## Failure Behavior

If the database insert fails, the generator logs the exception and raises `RuntimeError` rather than returning the unsaved record. This ensures CI and callers surface persistence failures (e.g. Cloudflare challenge errors) instead of silently succeeding.

## Related

- [[entities/pipeline]]
- [[entities/engine]]
- [[entities/market-data]]
- [[concepts/multi-horizon-reference]]
- [[concepts/ingestion]]
- [[concepts/backfilled-trades]]
- [[entities/fetch-daily-newsletter-tool]]
