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
FMPProvider.get_hourly_history()   → List of timestamped hourly bars (09:30 - 16:00 ET)
    ↓
fetch_regular_trading_hours_ohlc() → Strict RTH OHLC tuple (drops pre/post-market ticks)
    ↓
fetch_intraday_prices()            → (open, high, low, close) tuple (fallback to EOD history)
    ↓
compute_intraday_hit_metrics()     → (intraday_hit, intraday_direction_hit)
```

The `price_history` DB table includes `open`, `high`, `low`, `close` columns so cached reads preserve OHLC for future evaluations.

### Regular Session (9:30 AM – 4:00 PM ET) Price Guarantee

Historical price fetching prioritizes timestamped hourly/intraday bars clamped strictly to **`09:30:00 <= timestamp <= 16:00:00` ET**. This guarantees two critical invariants:
1. **Zero Extended-Hours Contamination**: Any pre-market (4:00 AM – 9:29 AM ET) or post-market (4:01 PM – 8:00 PM ET) price fluctuations are strictly discarded before computing High, Low, or Close metrics.
2. **Immediate Availability**: Full regular-session price action (including afternoon reversals) is captured immediately at 5:00 PM ET without waiting for delayed daily EOD consolidated tape table publishing.

If hourly bars are unavailable, `fetch_intraday_prices()` falls back to `MarketDataManager.get_history(ticker, days=10, force_refresh=True)`.

## Known Bugs & Fixes

### 1. OHLC Field Stripping (Fixed 2026-08-08)
- `MarketDataManager.get_history()` previously stripped OHLC fields from HistoryData on read/write. Fixed by persisting all four fields to `price_history`.

### 2. Cache Staleness False-Positive on EOD Close (Fixed 2026-08-27)
- `MarketDataManager.get_history()` treated 1-day old DB cache as valid (`age <= 4`), preventing `fetch_intraday_prices()` from seeing the new day's EOD bar. Fixed by adding an automatic fallback to `get_history(ticker, days=10, force_refresh=True)` when `target_date_str` is not in the cached results.

### 3. Premature EOD Cache & Regular Trading Hours Isolation (Fixed 2026-09-01)
- When running evaluation immediately at 5:04 PM ET, unfinalized EOD bars previously captured early morning lows ($761.17) instead of the full trading session ($759.48), causing false-negative `MISSED` evaluations. Fixed by implementing `fetch_regular_trading_hours_ohlc()`, which aggregates timestamped `09:30 - 16:00 ET` intraday bars directly and supports `--force` re-evaluations.

## Usage

- **Live evaluation** (`evaluate_daily_predictions`): Fetches Open, High, Low, Close prices via `MarketDataManager` and stores the metrics in the `daily_predictions` table.
- **Backtest evaluation** (`evaluate_backtest_prediction`): Uses the same function with FMP-based OHLC data.
- **Scoring**: The daily ratchet score formula uses intraday hit rate as a 35% weighted component alongside 55% close accuracy and 10% magnitude capture, minus a 50x Brier penalty.

## Related

- [[entities/daily-market-predictor]]
- [[entities/daily-predictor-backtest-arena]]
- [[concepts/auto-research-prompt-improver]]
