---
tags: [predictor, daily, intraday, sp500, autoresearch, deepseek]
category: entity
---

# Daily S&P Market Predictor and Autoresearch Loop

The **Daily S&P Market Predictor** generates 9:00 AM ET pre-market predictions for intraday S&P 500 (SPY) price action, determining whether the 4:00 PM ET Close price will be higher (`UP`) or lower (`DOWN`) than the 9:30 AM ET Open price ($\text{Direction} = \text{UP if } \text{Close} \ge \text{Open} \text{ else DOWN}$).

## Key Features

1. **Pre-Market Inference (9:00 AM ET)**:
   - Command: `python main.py daily-predictor [--ticker SPY]`
   - Model: **DeepSeek Flash** (`deepseek-v4-flash`) with Instructor structured output (`DailyPredictionOutput`).
   - Context: Synthesizes technical indicators, overnight futures (ES/NQ), macro news summaries, and market barometer data.

2. **Post-Market Evaluation (5:15 PM EDT / 4:15 PM EST)**:
   - Command: `python main.py evaluate-daily-predictions`
   - Scopes today's 9:30 AM Open and 4:00 PM Close prices from market data feeds safely after market close.
   - Calculates **Directional Accuracy** (`is_correct`) and **Brier Calibration Score** ($\text{Brier} = (p - y)^2$, where $p = \text{confidence}/100.0$).

3. **Twice-Weekly Prompt Evolution (Wed/Sun 6:00 PM ET)**:
   - Command: `python main.py daily-autoresearch`
   - Evaluates predictions over recent 3–4 trading days against all-time baseline in `prompt_experiments` (`prompt_name: "DAILY_PREDICTOR_PROMPT"`).
   - Applies ratchet logic: if recent performance beats baseline, establishes new baseline; if lower, reverts to baseline prompt.
   - Mutates mutable strategy section using DeepSeek Flash meta-researcher.

4. **Web Frontend (`/daily-predictions`)**:
   - Live dashboard featuring Hero Prediction Card, Directional Accuracy %, Brier Calibration stats, Historical Predictions Log table, and Autoresearch Prompt Arena.

## Database Schema

- `public.daily_predictions`: Stores predictions, actual Open/Close prices, correctness, and Brier scores.
- `public.prompt_experiments`: Tracks `DAILY_PREDICTOR_PROMPT` variants, statuses, and performance metrics.

## Related

- [[entities/sector-predictor-arena]] — Sector predictor arena comparison
- [[entities/autoresearch]] — Portfolio auto-research subsystem
- [[entities/database]] — Core database schema and prompt tracking tables
