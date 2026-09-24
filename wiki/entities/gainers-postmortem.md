---
tags: [postmortem, audit, gainers, memory, openai]
category: entity
---

# Missed Gainers Post-Mortem

Automated adversarial audit pipeline that discovers daily, weekly, and monthly market top gainers, cross-references them against internal prediction logs, and diagnoses why Benchify models missed or faded the move.

## Overview

While traditional post-analysis in [[entities/pipeline]] audits trades that the system already executed, the Missed Gainers Post-Mortem diagnoses opportunity cost and false negatives. It identifies stocks and sectors that produced substantial market gains across 1-day, 5-day (weekly), and 1-month horizons, then challenges OpenAI `gpt-5.6-luna` to diagnose the root cause of the blind spot.

The module is implemented as an isolated vertical slice island in `apps/engine/analysis/gainers_postmortem.py`.

## Data Pipeline & Liquidity Guardrails

The pipeline queries Financial Modeling Prep (FMP) using stable endpoints with strict liquidity filters:

1. **Daily Movers:** Fetches `https://financialmodelingprep.com/stable/biggest-gainers`. Discards micro-cap and sub-penny stocks by requiring `price >= $2.00`.
2. **Weekly Movers (5D):** Queries `https://financialmodelingprep.com/stable/company-screener` for actively trading US equities with market capitalization `>= $2B`. Combines these with the 14 standard sector ETFs (`XLK`, `SMH`, `XLE`, `XLF`, `XLV`, etc.) and batches requests to `https://financialmodelingprep.com/stable/stock-price-change` to sort by `5D` return.
3. **Monthly Movers (1M):** Evaluates the same liquid universe sorted by `1M` percentage return.
4. **Catalyst Enrichment:** Pulls the 3 most recent ticker headlines from `https://financialmodelingprep.com/stable/news/stock` to ground the diagnosis in verified news events.

## Internal Prediction Cross-Referencing

For each target gainer, the auditor inspects Supabase tables across the corresponding lookback window:

- **`decisions` table:** Checks if any trading agent (OpenAI, Anthropic, Gemini, DeepSeek, MiniMax) evaluated the ticker, recording the signal (`BUY`, `HOLD`, `SELL`), model confidence, and rationale.
- **`trades` table:** Verifies whether any portfolio executed an actual position.
- **`sector_predictions` table:** Evaluates whether our sector forecasting model anticipated strength in the parent sector or misidentified it as a worst-performing sector.

A ticker is classified as missed if no model issued a `BUY` or if existing positions were exited prematurely.

## Adversarial LLM Diagnosis

Diagnosis is performed exclusively by **`gpt-5.6-luna`** using Instructor with `mode=instructor.Mode.JSON` to enable active reasoning (`reasoning_effort="medium"`). Because no function tools are passed in the prompt payload, OpenAI's chat completions gateway cleanly executes reasoning tokens without 400 parameter errors.

The model outputs a typed `MissedGainerDiagnosis` record classifying the root cause:

- `BLINDSPOT_CATALYST`: Catalyst was public and knowable in advance, but dismissed by agents.
- `EXCESSIVE_RISK_AVERSION`: Agent evaluated the stock but rejected it due to valuation or multiple compression fears.
- `MOMENTUM_TIMIDITY`: Parent sector or technical momentum was breaking out, but single-stock agents faded the move.
- `COVERAGE_GAP`: Stock fell outside active universe surveillance, meaning zero decisions were generated.
- `PREMATURE_EXIT`: Model entered the trade but cut winners too early on fixed-percentage targets instead of trailing stops.
- `UNPREDICTABLE_SURPRISE`: Binary shock, unannounced takeover, or clinical trial surprise that could not be forecasted.

## Long-Term Memory Persistence

Post-mortems are saved directly into the Supabase `memories` table:

- `memory_type`: `POST_MORTEM`
- `importance_score`: 8
- `metadata`: Contains `ticker`, `timeframe`, `return_pct`, `predictable_score`, `category`, and `actual_catalyst`.
- **7-Day Deduplication:** Checks for identical ticker and timeframe records created within the last 7 days to prevent database bloat on repeated runs.

Because they are recorded as first-class `POST_MORTEM` memories, these insights immediately surface in the web app's `/memories` Post-Mortem tab, appear on the Today dashboard Agent Insights feed, and feed future agent RAG retrieval via `search_past_memories`.

## CLI Usage & CI/CD Schedule

### CLI Command
Run manually or during diagnostic investigations:
```bash
./apps/engine/.venv/bin/python3 apps/engine/main.py gainers-postmortem --timeframe all --limit 3
```

Options:
- `--timeframe`: `daily`, `weekly`, `monthly`, or `all` (default: `all`).
- `--limit`: Number of top gainers to audit per timeframe (default: 3).
- `--no-save-memory`: Dry-run mode without writing to Supabase `memories`.

### CI/CD Cadence
Scheduled in `.github/workflows/audit.yml` every Friday at 16:00 EST (21:00 UTC) at regular trading hours close, evaluating the full week's missed winners before weekend portfolio rebalancing.

## Related

- [[concepts/memory-feedback]]
- [[entities/pipeline]]
- [[entities/autoresearch]]
- [[entities/web-app]]
