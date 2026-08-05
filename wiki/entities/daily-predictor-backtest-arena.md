---
tags: [daily-predictor, backtest, arena, prompt-mutation, temporal-sandbox]
category: entity
---

# Daily Predictor Backtest Arena

A temporal sandbox for auditing and improving the S&P 500 (SPY) daily open-to-close prediction pipeline. It runs simulated prediction/evaluation cycles over historical dates using a local SQLite database, then applies a meta-researcher (DeepSeek Flash) to mutate the mutable strategy instructions of the daily predictor prompt. The results are displayed in a dedicated web UI that mirrors the live Daily Predictor page but scoped to backtest data.

## Engine Backtest Pipeline

- **Command**: `python apps/engine/main.py backtest-daily-autoresearch --start-date YYYY-MM-DD --weeks N`
- **Database**: Local SQLite file `.backtest_daily.db` with tables `daily_predictions` and `prompt_experiments` (mirroring Supabase schema, with `is_backtest = 1`).
- **Price Source**: Attempts `yfinance` for real historical open/close; falls back to deterministic synthetic prices for offline testing.
- **Daily Cycle**:
  1. **09:00 AM ET** – Simulated prediction using the active prompt variant (DeepSeek Flash).
  2. **05:15 PM ET** – Evaluation against actual open/close, computing correctness and Brier calibration score.
- **Weekly Ratchet**: At the end of each simulated week, a meta-researcher LLM (DeepSeek Flash) generates a new mutable strategy section based on the current ratchet score, and the new prompt variant is stored as an active experiment.

## Web UI

- **Route**: `/daily-predictions-backtest`
- **Page**: `DailyPredictionsBacktestPage` – displays:
  - Metrics overview (directional accuracy, Brier score, total runs, experiment count)
  - Historical predictions log table (date, ticker, predicted direction, confidence, actual prices, outcome, Brier score, prompt variant tag)
  - Prompt Experiments Arena with variant lineage sidebar and full prompt content viewer
- **Data Fetching**: Uses `fetchDailyPredictorBacktestPredictions` and `fetchDailyPredictorBacktestExperiments` which filter Supabase by `is_backtest = true` or `prompt_variant_tag` containing `backtest`.

## Seeding the Live Prompt

- **Command**: `python apps/engine/main.py seed-daily-predictor`
- **Function**: `seed_daily_predictor_prompt()` inserts the current `DAILY_PREDICTOR_PROMPT` (optimized via backtest) as the active live baseline in Supabase, demoting any previous active prompt to `saved`.

## Related

- [[entities/daily-market-predictor]] – Live daily prediction pipeline
- [[entities/autoresearch-arena]] – Portfolio-level prompt experiment history
- [[concepts/temporal-sandboxing]] – Local DB and simulated execution pattern
- [[concepts/prompt-section-splitting]] – Splitting prompt into header, mutable strategies, and footer
- [[concepts/auto-research-prompt-improver]] – Meta-researcher mutation concept
