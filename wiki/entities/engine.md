---
tags: [engine, python, pipeline, data]
category: entity
---

# Engine

The Python data engine (`apps/engine/`) is the core pipeline that ingests financial news, runs LLM analysis, builds consensus, validates trades, and executes them. It is organized into modules under `apps/engine/` with a `main.py` entry point.

## Modules

- **`core/`** — Configuration, LLM client wrappers, tool definitions, and prompt templates
- **`execution/`** — Market data management, order placement, portfolio operations, and trade settlement
- **`tasks/`** — Orchestrated pipeline tasks (daily predictor, ingestion, analysis, consensus, execution, feedback)
- **`tests/`** — Test suite with zero-warning policy and dependency injection patterns
- **`hotspots.py`** — Git churn forensics and temporal coupling analyzer

## Market Data Management

The `execution/market_data.py` module provides `MarketDataManager`, the central class for fetching live and historical market data. It supports multiple data providers via a provider abstraction.

### Aftermarket / Pre-Market Quote Provider

`MarketDataManager` now supports an optional provider with a `get_aftermarket_quote(ticker)` method. When available, `get_premarket_quote()` first attempts to fetch a dedicated aftermarket quote from this provider. If the provider returns a valid price (>0), that price is used as the pre-market price. Otherwise, it falls back to the standard quote from `get_quote()`. This ensures the most accurate pre-market pricing is used for gap analysis.

Key behavior:
- Provider method `get_aftermarket_quote` returns a dict with `price`, `bid`, `ask`, `volume`
- If provider returns `None` or raises an exception, fallback to standard quote
- When an aftermarket quote is present, the previous close is extracted from `quote.price` (prior regular session close), with fallback to `quote.previous_close` or historical data when aftermarket pricing is absent

### Concurrent Proxy Quote Fetching

In `tasks/daily_predictor.py`, the `get_daily_market_context` function now fetches pre-market quotes for macro proxies (QQQ, DIA, IWM, IEF, GLD, USO, UUP) concurrently using `asyncio.gather`. Partial failures (e.g., a single proxy API timeout) are handled gracefully — the failed proxy is skipped without breaking the entire context generation. This improves reliability and speed.

## Related

- [[concepts/execution]]
- [[entities/daily-market-predictor]]
- [[entities/macro-tracker]]
- [[concepts/ingestion]]
- [[concepts/code-hotspots]]
