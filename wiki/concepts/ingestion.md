---
tags: [ingestion, pipeline, economic-calendar, catalyst-radar]
category: concept
---

# Ingestion

The ingestion phase is the first stage of the daily pipeline (see [[entities/pipeline]]): it fetches raw market inputs — daily trading newsletters, the economic calendar, and government data — parses them into structured events, and persists the noteworthy ones as memories and future catalysts for the [[concepts/catalyst-radar]] and downstream analysis.

## Newsletter Scraping

Daily market newsletters are fetched and ingested as raw text for LLM parsing. The canonical fetch tool is [[entities/fetch-daily-newsletter-tool]].

## Economic Calendar Ingestion

The `CalendarPipeline` (`apps/engine/ingest/calendar.py`) fetches the economic calendar HTML, parses nested event rows, and sends the resulting events to DeepSeek for relevance analysis.

### Critical-Economy Filtering

Events are filtered to critical global economies and systemic macro countries before any LLM call. `is_critical_country()` checks the event country against `ALLOWED_CALENDAR_COUNTRIES`:

- United States, Canada, Euro Area, Germany, France, United Kingdom, Italy, Spain, Switzerland, Netherlands, China, India, Japan, South Korea
- `global` for systemic macro events

`CalendarPipeline.filter_events()` drops everything else (Australia, Brazil, Turkey, South Africa, Mexico, Russia, Indonesia, etc.), keeping focus on releases that can plausibly move US equity markets.

### DeepSeek Relevance Analysis

The prompt focuses strictly on events that move US equity markets (S&P 500, sector ETFs, Treasuries, tech/commodities) and asks DeepSeek to label matches:

- `CENTRAL_BANK` — Fed, ECB, BoJ, BoE, PBOC decisions
- `INFLATION` — US CPI, Core CPI, PPI, PCE, Eurozone CPI
- `EMPLOYMENT` — US NFP, Jobless Claims, Unemployment
- `GDP` — US, Euro Area, China, Japan, Germany releases
- `GEOPOLITICAL` — G7/G20 summits, OPEC/OPEC+ quotas, bilateral US trade talks
- `HOLIDAY` — US NYSE/Nasdaq holidays

Events with Importance Score >= 8 or matching a CALENDAR STRATEGY (`Pre-ECB/Fed Drift`, etc.) are persisted as memories flagged `is_future_catalyst: true`, feeding [[concepts/catalyst-radar]]. Titles are normalized later by the radar's title cleaner (see [[concepts/catalyst-radar]]).

## Government Spending, Liquidity & Contract Ingestion

The `GovernmentPipeline` (`apps/engine/ingest/government.py` and `apps/engine/ingest/government_fetchers.py`) ingests official government balance sheet operations, fiscal deficits, and procurement contracts outside the daily newsletter and market consensus loop:

- **US Treasury General Account (TGA) & Debt**: Connects to `fiscaldata.treasury.gov` (Daily Treasury Statement `/v1/accounting/dts/operating_cash_balance` and Debt to the Penny `/v2/accounting/od/debt_to_penny`) to persist daily operating cash balances, debt held by the public, intragovernmental holdings, and monthly budget deficits into `gov_macro_liquidity`.
- **Federal Contract Procurement (US & Canada)**:
  - **USAspending**: Ingests US federal contract awards from `api.usaspending.gov` with award amounts, recipient corporations, agency affiliations, and contract IDs.
  - **CanadaBuys**: Ingests Canadian federal contract awards from `canadabuys.canada.ca` via Open Government CKAN datasets to capture resource, infrastructure, and defense contract pipelines.
  - Materialized into `gov_contracts`.
- **Catalyst Memories**: Flags major contract pipelines, critical minerals incentives, and budget expirations for [[concepts/catalyst-radar]].
- **Institutional Whale & Activist Blockholders**: The pipeline (`apps/engine/ingest/whale_fetchers.py`) ingests real-time SEC Schedule 13D and 13G beneficial ownership disclosures (>5% stake acquisitions, activist entries, and complete position liquidations) for active universe tickers into `institutional_whale_stakes`.

## Dry-Run Mode & After-Hours Simulation

The ingestion pipeline supports an end-to-end dry-run simulation mode via the `--dry-run` CLI flag (or workflow dispatch input in `.github/workflows/ingest.yml`). This enables developers and automated health checks to verify the full multi-model extraction, consensus, and decision pipeline outside regular US market hours:

- **Market Hours Bypass**: Bypasses the `is_market_open()` gate to allow execution during evening, weekend, or holiday hours.
- **Snapshot Fallback**: If no Gmail newsletters have arrived for the current trading day, the pipeline automatically falls back to the most recent record in `newsletter_snapshots` from Supabase to provide realistic market inputs.
- **Zero-Mutation Guardrails**: Dust cleanup liquidations, portfolio ledger updates (`Portfolio.execute_trade`), and Alpaca limit order submissions are bypassed with simulated logs.
- **Mock Decision Attribution**: Signal attribution calls route through `_record_decision` returning mock decision IDs, verifying signal processing end-to-end without mutating the production `decisions` table.

## Related

- [[concepts/catalyst-radar]]
- [[entities/pipeline]]
- [[entities/engine]]
- [[entities/tool-audit]]
- [[entities/fetch-daily-newsletter-tool]]
