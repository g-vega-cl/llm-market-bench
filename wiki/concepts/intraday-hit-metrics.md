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
FMPProvider.get_history()          → HistoryData (has open, high, low, price)
    ↓
MarketDataManager.get_history()    → list[dict] (must include open, high, low)
    ↓
fetch_intraday_prices()            → (open, high, low, close) tuple
    ↓
compute_intraday_hit_metrics()     → (intraday_hit, intraday_direction_hit)
```

The `price_history` DB table now includes `open`, `high`, `low`, `close` columns (nullable) so cached reads preserve OHLC for future evaluations.

## Known Bug (Fixed 2026-08-08)

**Symptom**: `intraday_hit` was always `False` for non-zero targets despite prices genuinely reaching the target.

**Root cause**: `MarketDataManager.get_history()` was stripping `open`/`high`/`low` from `HistoryData` in two places:
1. The DB read path returned only `{price, fetched_at}`.
2. The DB write path only persisted `price`, `market_cap`, `fetched_at` to `price_history`.

As a result, `fetch_intraday_prices()` fell back to `max(open, close)` / `min(open, close)` — which collapsed all four OHLC values to the same close price, making the max intraday return 0%.

**Fix**:
- Migration `20260808000000_add_ohlc_to_price_history.sql` adds `open`, `high`, `low`, `close` nullable columns to `price_history`.
- `MarketDataManager.get_history()` now reads and writes all four OHLC fields.
- Existing rows and callers that only use `price` are unaffected (nullable, additive dict keys).

**Confirmed instance**: SPY prediction for 2026-08-07 (expected +0.25% UP). Actual high was +0.375% above open — correctly recorded as `intraday_hit = true` after the fix.

## Usage

- **Live evaluation** (`evaluate_daily_predictions`): Fetches Open, High, Low, Close prices via `MarketDataManager` and stores the metrics in the `daily_predictions` table.
- **Backtest evaluation** (`evaluate_backtest_prediction`): Uses the same function with FMP-based OHLC data.
- **Scoring**: The daily ratchet score formula uses intraday hit rate as a 30% weighted component alongside 70% close accuracy, minus a Brier penalty.

## Related

- [[entities/daily-market-predictor]]
- [[entities/daily-predictor-backtest-arena]]
- [[concepts/auto-research-prompt-improver]]
