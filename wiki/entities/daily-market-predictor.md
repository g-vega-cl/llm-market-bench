---
tags: [daily-predictor, prediction, spy, evaluation, alpaca]
category: entity
---

# Daily S&P Market Predictor

The **Daily S&P Market Predictor** generates 9:15 AM ET pre-market predictions for the S&P 500 (SPY) open-to-close direction. Each participating model produces a directional call (`UP`/`DOWN`), a confidence, and (for most models) an expected return percentage. Predictions are stored in the `daily_predictions` table and drive both scoring and the systematic daily SPY trading tracks.

## Pipeline

1. **Prediction Generation** — Models are prompted pre-market with injected market context and emit a direction, confidence, and expected return.
   - **Pre-Market Hours & Idempotency Guard**: `run_daily_prediction` strictly requires execution within the pre-market window (04:00 to 09:30 ET). If triggered after 9:30 AM ET market open or before 4:00 AM ET, it refuses to run for the current session without `--force`. Furthermore, it checks if predictions already exist for the target date in `daily_predictions` and refuses to clobber existing records. In `.github/workflows/daily-predictor.yml`, the workflow safety check skips `daily-predictor` anytime the current time is $\ge 13:30$ UTC (9:30 AM ET).
2. **Evaluation** — After the close, `apps/engine/tasks/evaluate_daily_predictions.py` scores each prediction against actual intraday prices.
   - **Non-Trading Day Purging**: If price data cannot be fetched and the target date was a non-trading day (weekend or market holiday), deletes the invalid prediction from `daily_predictions` to prevent indefinite retry loops.
   - Scopes today's 9:30 AM Open, High, Low, and 4:00 PM Close prices safely after market close by prioritizing timestamped Regular Trading Hours (`09:30:00 <= timestamp <= 16:00:00` ET) hourly bars (with automatic fallback to FMP `/historical-price-eod/full` EOD history). This guarantees zero extended-hours/post-market price contamination while immediately capturing afternoon price extremes.
   - Calculates **Directional Accuracy** (`is_correct`), **Intraday Target Hit Rate** (`intraday_hit`), **Intraday Direction Hit Rate** (`intraday_direction_hit`), and **Brier Calibration Score** ($\text{Brier} = (p - y)^2$, where $p = \text{confidence}/100.0$).

## System Portfolio Execution

Execution is decoupled into a real-time live trading lifecycle rather than a retroactive backfill:

- **Pre-Market MOO Entry (~9:20 AM ET)**: Dispatched via `main.py daily-trade --action entry` in `.github/workflows/daily-predictor.yml` before the 9:28 AM ET Alpaca cutoff. For `UP` signals, submits `TimeInForce.OPG` market orders to Alpaca for the 9:30:00 AM opening cross and logs active positions in `portfolio_positions`. For `DOWN` signals, logs virtual `SHORT` trades in the `trades` table (no Alpaca shorting).
- **Target-Exit Portfolios** (`sys-daily-spy-{model_name}`): At ~9:35 AM ET (morning ingestion hook), submits an Alpaca limit sell order at the profit target price ($P_{open} \times (1 + \text{expected\_return\_pct} / 100)$). Requires a non-zero expected return percentage (direction-only models like Jev are excluded).
- **3:30 PM Afternoon Close Exit**: At ~3:30 PM ET (`main.py run_ingest` afternoon hook), cancels open target orders, liquidates held SPY shares on Alpaca and Supabase, closes virtual short trades, and realizes PnL with zero retroactive backfilling.
- **Post-Market Evaluation (5:00 PM ET)**: Focuses purely on Brier calibration, direction accuracy metrics, and GPT-5.6 Luna postmortem audit. Retroactive backfilling in `evaluate_daily_predictions` is gated behind `--backfill-trades` (defaults to `False`).

## Daily Post-Mortem Island (`analysis/daily_postmortem.py`)

- Command: `python main.py daily-postmortem [--target-date YYYY-MM-DD] [--force]`
- Triggered automatically upon completion of `evaluate_daily_predictions` when predictions are evaluated.

## Related

- [[concepts/system-portfolios]]
- [[concepts/brier-score]]
- [[concepts/alpaca-order-sync]]
- [[entities/pipeline]]
