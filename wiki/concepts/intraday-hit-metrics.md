---
tags: [evaluation, daily-predictions, intraday, metrics]
category: concept
---

# Intraday Hit Metrics

A two-dimensional evaluation system for daily market predictions that measures both end-of-day directional accuracy and intraday price target achievement.

## Metrics

Two boolean flags are computed at evaluation time:

- **`intraday_hit`** — `True` if the market price reached or surpassed the predicted `expected_return_pct` at any point during the trading session. For example, if the prediction was "UP +0.35%", `intraday_hit` is `True` if the high price rose at least 0.35% above the open, even if the stock closed lower.
- **`intraday_direction_hit`** — `True` if the market price moved in the predicted direction at any point intraday (high > open for UP predictions, low < open for DOWN predictions).

## Computation

The function `compute_intraday_hit_metrics()` in `tasks/evaluate_daily_predictions.py` implements the logic. It is shared between the live evaluation pipeline and the backtest system.

## Usage

- **Live evaluation** (`evaluate_daily_predictions`): Fetches Open, High, Low, Close prices via `MarketDataManager` and stores the metrics in the `daily_predictions` table.
- **Backtest evaluation** (`evaluate_backtest_prediction`): Uses the same function with yfinance-based OHLC data.
- **Scoring**: The daily ratchet score formula uses intraday hit rate as a 30% weighted component alongside 70% close accuracy, minus a Brier penalty.

## Related

- [[entities/daily-market-predictor]]
- [[entities/daily-predictor-backtest-arena]]
- [[concepts/auto-research-prompt-improver]]
