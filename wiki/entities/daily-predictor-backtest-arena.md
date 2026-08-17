---
tags: [backtest, daily-predictions, arena, evaluation]
category: entity
---

# Daily Predictor Backtest Arena

Web UI and engine backtest system for S&P 500 daily open-to-close predictions with prompt mutation. The arena provides a full simulation environment where prompt variants are tested against historical data and scored using a composite ratchet metric.

## Architecture

The backtest system lives in `apps/engine/tasks/backtest_daily_autoresearch.py` and uses a local SQLite database (`data/backtest_daily.db`) for storing predictions and prompt experiments, completely decoupled from the Supabase production database.

### Key Components

- **`init_backtest_daily_db()`** — Creates SQLite tables (`daily_predictions`, `prompt_experiments`). Includes **auto-migration**: if columns are missing from previous runs (e.g., `actual_high_price`, `actual_low_price`, `intraday_hit`, `intraday_direction_hit`), they are added via `ALTER TABLE`.
- **`reset_backtest_daily_db()`** — Drops and recreates tables for a clean slate.
- **`fetch_historical_spy_prices(target_date)`** — Fetches Open, High, Low, and Close prices via yfinance, with a deterministic fallback when data is unavailable.
- **`evaluate_backtest_prediction()`** (formerly `evaluate_simulated_daily_prediction`) — Evaluates a single prediction against actual OHLC prices, computing `is_correct`, `intraday_hit`, `intraday_direction_hit`, and `brier_score`. The old name is preserved as an alias for backward compatibility.
- **`run_backtest_daily_autoresearch()`** — Runs the full backtest cycle: generates predictions via simulated trading day, evaluates them, computes aggregate scores, and triggers prompt mutation if performance beats baseline.

## Intraday Hit Metrics

Two new evaluation dimensions were added alongside the existing EOD directional accuracy:

- **`intraday_hit`** — `True` if the market price reached or surpassed the predicted `expected_return_pct` at any point during the trading session (e.g., price hit +0.35% high even if it closed at -0.20%).
- **`intraday_direction_hit`** — `True` if the market price moved in the predicted direction intraday (high > open for UP, low < open for DOWN).

These metrics are computed via `compute_intraday_hit_metrics()` in `tasks/evaluate_daily_predictions.py`, which is shared between live evaluation and backtest.

## Scoring Formula

The composite multi-factor ratchet score used for prompt mutation is:

$$
\text{Ratchet Score} = (0.55 \times \text{close\_accuracy\_pct}) + (0.35 \times \text{intraday\_hit\_pct}) + (0.10 \times \text{magnitude\_capture\_pct}) - (\text{mean\_brier} \times 50.0)
$$

- **Close Accuracy %** (55% weight): Percentage of predictions where the EOD close direction matched the prediction.
- **Intraday Hit %** (35% weight): Percentage of predictions where the intraday target was hit (falls back to `is_correct` when `intraday_hit` is null).
- **Magnitude Capture %** (10% weight): Percentage of the actual move captured on correct predictions that hit target ($\min(1.0, |\text{expected}|/\max(|\text{peak}|, |\text{close}|)) \times 100$).
- **Brier penalty**: Mean Brier score multiplied by 50, subtracted from the weighted sum.

## Web UI

The `/daily-predictions` page displays a metrics dashboard including the new Intraday Target Hit card (40% weight), and a predictions table with an 
