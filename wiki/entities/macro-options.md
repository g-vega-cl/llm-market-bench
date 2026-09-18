---
tags: [macro, options, market-data, engine]
category: entity
---

# Macro Options

Macro Options is a module in the engine that fetches and formats macro options data, including economic indicators and market context, for use in analysis and reporting.

## Overview

This component retrieves macro options metrics from external data sources, caches responses, and formats them into markdown tables for terminal or markdown summaries. It supports multiple tickers and handles empty result sets gracefully.

## Key Features

- **Cross-Asset Coverage**: Fetches and aggregates derivatives positioning across key macro proxies (`SPY`, `QQQ`, `IWM`, `GLD`).
- **Self-Healing Spot Price Resolution**: Operates on top of [[entities/massive-options]] self-healing spot resolution, ensuring underlying spot prices and bounded strike chains use live quotes or Polygon `/prev` close bars rather than synthetic fallbacks.
- **Rate-Resilient Pacing**: Requests flow through a token-bucket rate limiter with individual ticker timeouts, avoiding 429 burst errors on Free Tier plans.
- **Supabase Cache Integration**: Caches responses in `options_data_cache` with a 1-hour TTL, enabling sub-second cache hits for repeated queries.
- **Dense Comparison Markdown**: Formats metrics (Put/Call ratios, Max Pain, ATM IV, 25-delta skew) into compact comparison tables for terminal summaries, newsletters, and predictors.

## Usage

Used by [[entities/generated-newsletters]] (`get_newsletter_options_context`) and [[entities/daily-market-predictor]] (`get_daily_market_context`) to inject verified derivatives positioning directly into model prompts.

## Related

- [[entities/economic-releases]]
- [[entities/massive-options]]
- [[entities/generated-newsletters]]
- [[entities/daily-market-predictor]]
- [[entities/engine]]
