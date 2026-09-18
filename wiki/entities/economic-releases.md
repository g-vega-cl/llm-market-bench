---
tags: [economic-releases, fmp, data-ingestion, macro]
category: entity
---

# Economic Releases

Live scheduled and released economic indicator integration via Financial Modeling Prep (FMP) `/stable/economic-calendar`. Provides real-time CPI, PPI, Nonfarm Payrolls, Retail Sales, Unemployment Rate, GDP, and other macro prints with actual vs consensus surprises, release status, and Eastern Time formatting.

## Overview

The Economic Releases module (`apps/engine/core/economic_releases.py`) fetches and caches macroeconomic data releases from FMP. It is used by the daily market predictor and newsletter generator to inject live morning prints (e.g., 8:30 AM ET CPI/PPI/Jobs) into LLM context. It is also available as the canonical agent tool `get_today_economic_releases`.

## Data Model

Each release is represented by the `EconomicEvent` dataclass:

- `date`, `time_et` — UTC timestamp converted to Eastern Time
- `country`, `event`, `impact` — metadata (e.g., "US", "CPI s.a (Aug)", "High")
- `actual`, `estimate`, `previous` — numerical values (nullable)
- `surprise` — computed as `actual - estimate` when both are available
- `change`, `change_pct` — absolute and percentage change from previous
- `status` — `"RELEASED"` if `actual` is not `None`, else `"PENDING"`

## Caching

A 30-minute in-memory TTL cache (`DEFAULT_CACHE_TTL_SECONDS = 1800`) keyed by `(from_date, to_date, country)`. Callers can bypass with `force_refresh=True`.

## API Endpoint

`https://financialmodelingprep.com/stable/economic-calendar?apikey=...&from=YYYY-MM-DD&to=YYYY-MM-DD`

Requires `FMP_API_KEY` environment variable. Returns a JSON array; each item is parsed and filtered by country.

## Usage

### In Daily Predictor

`get_daily_market_context()` in `tasks/daily_predictor.py` calls `get_today_economic_releases_summary()` and injects the formatted block into the context sent to LLMs before calendar scenarios, newsletter briefings, and technical indicators.

### In Newsletter Generator

`generate_daily_newsletter()` in `tasks/newsletter_generator.py` passes the economic releases context to `_call_deepseek_flash()` as `economic_releases_context`, which is inserted into the system prompt under "Today's Live Economic Data Releases (Actual vs Consensus)".

### As Agent Tool

Tool name: `get_today_economic_releases`
Parameters: `target_date` (optional, default today ET), `country` (optional, default "US")
Returns: Formatted markdown with released and pending events.

Registered in `CANONICAL_TOOLS_REGISTRY` in `core/llm/tools.py` and dispatched via `execute_get_today_economic_releases_tool()`.

## Related

- [[entities/daily-market-predictor]] — consumes economic releases in daily context
- [[entities/generated-newsletters]] — includes economic releases in newsletter synthesis
- [[concepts/ingestion]] — covers both forward calendar scraping and live morning releases
- [[entities/engine]] — part of the Python data engine
