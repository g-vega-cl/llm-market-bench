---
tags: [daily, prediction, engine]
category: entity
---

# Daily Market Predictor

A pipeline task that predicts the daily directional move (up/down) for a given ticker (default SPY) using market context—most notably the latest macro regime signals and the most recent market sentiment from the `market_feeling` table.

## Implementation

The task `get_daily_market_context()` gathers two primary data points:
- **Macro regime**: current state for equities pulled from `global_macro_state`.
- **Market sentiment**: the newest row from `market_feeling`, reading the `sentiment_label` column (formerly `feeling`) and `news_summary`. This gives the LLM a concise emotional/sentimental backdrop for its prediction.

The assembled context is injected into the LLM prompt to produce a binary (up/down) forecast.

## Related
- [[concepts/market-feeling]]
- [[entities/macro-tracker]]
- [[entities/engine]]
