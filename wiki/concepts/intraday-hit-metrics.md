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

## Data Pipeline

OHLC prices flow through the following chain to reach `compute_intraday_hit_metrics()`:

```
FMPProvider.get_history()          → HistoryData (official 4:00 PM EOD bar: open, high, low, close)
    ↓
MarketDataManager.get_history()    → list[dict] (persists and reads open, high, low, close)
    ↓
fetch_intraday_prices()            → (open, high, low, close) tuple (force_refresh fallback if missing)
    ↓
compute_intraday_hit_metrics()     → (intraday_hit, intraday_direction_hit)
```

The `price_history` DB table includes `open`, `high`, `low`, `close` columns so cached reads preserve OHLC for future evaluations.

### Regular Session (4:00 PM ET) Price Guarantee

Historical price fetching uses FMP's `/historical-price-eod/full` endpoint rather than real-time quote feeds. This isolates evaluation metrics from extended-hours and after-hours volatility, ensuring that `open`, `high`, `low`, and `close` strictly reflect the official 9:30 AM to 4:00 PM ET regular trading session.

If the target session date is not present in the local database cache window at evaluation time (5:15 PM ET), `fetch_intraday_prices()` automatically issues `force_refresh=True` to the provider to fetch and cache the newly settled 4:00 PM EOD candle.

## Known Bugs & Fixes

### 1. OHLC Field Stripping (Fixed 2026-08-08)
- `MarketDataManager.get_history()` previously stripped OHLC fields from HistoryData on read/write. Fixed by persisting all four fields to `price_history`.

### 2. Cache Staleness False-Positive on EOD Close (Fixed 2026-08-27)
- `MarketDataManager.get_history()` treated 1-day old DB cache as valid (`age <= 4`), preventing `fetch_intraday_prices()` from seeing the new day's EOD bar. Fixed by adding an automatic fallback to `get_history(ticker, days=10, force_refresh=True)` when `target_date_str` is not in the cached results.

## Usage

- **Live evaluation** (`evaluate_daily_predictions`): Fetches Open, High, Low, Close prices via `MarketDataManager` and stores the metrics in the `daily_predictions` table.
- **Backtest evaluation** (`evaluate_backtest_prediction`): Uses the same function with FMP-based OHLC data.
- **Scoring**: The daily ratchet score formula uses intraday hit rate as a 35% weighted component alongside 55% close accuracy and 10% magnitude capture, minus a 50x Brier penalty.

## Related

- [[entities/daily-market-predictor]]
- [[entities/daily-predictor-backtest-arena]]
- [[concepts/auto-research-prompt-improver]]
