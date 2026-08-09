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
   - Context: Synthesizes technical indicators (SMA20, 5-day return via FMP `MarketDataManager`) and canonical tools context (`execute_get_global_macro_context_tool`, `execute_get_volatility_index_details_tool`, `execute_market_health_barometer_tool`, `execute_get_market_feeling_tool`).
   - **Zero-Mean Anti-Bias Mandate**: System prompt enforces a zero-mean distribution baseline (~50/50 UP vs DOWN) to eliminate pre-trained LLM long-term market drift bias. Requires strictly symmetric evaluation of bearish breakdown signals (VWAP resistance, RSI > 70 overbought exhaustion, yield surges) alongside bullish momentum signals.

2. **Post-Market Evaluation (5:15 PM EDT / 4:15 PM EST)**:
   - Command: `python main.py evaluate-daily-predictions`
   - Scopes today's 9:30 AM Open, High, Low, and 4:00 PM Close prices safely after market close via FMP `MarketDataManager` (skips evaluation if target date hasn't closed yet).
   - Calculates **Directional Accuracy** (`is_correct`), **Intraday Target Hit Rate** (`intraday_hit`), **Intraday Direction Hit Rate** (`intraday_direction_hit`), and **Brier Calibration Score** ($\text{Brier} = (p - y)^2$, where $p = \text{confidence}/100.0$).
   - `intraday_hit` evaluates whether the stock reached or surpassed the predicted target return percentage (`expected_return_pct`) at any point between Open and Close (e.g. hitting +0.35% intraday high even if it closed at -0.20%).

3. **Twice-Weekly Prompt Evolution & Performance Ratchet (Sun & Wed 6:00 PM ET)**:
   - Command: `python main.py daily-autoresearch`
   - Evaluates predictions over recent trading days against baseline in `prompt_experiments` (`prompt_name: "DAILY_PREDICTOR_PROMPT"`).
   - Combined Ratchet Score formula:
     $$\text{Ratchet Score} = (0.70 \times \text{close\_accuracy\_pct}) + (0.30 \times \text{intraday\_hit\_pct}) - (\text{mean\_brier} \times 50.0)$$
   - Applies ratchet logic: if recent performance beats baseline, establishes new baseline; if lower, reverts to baseline prompt.
   - Mutates mutable strategy section using DeepSeek Flash meta-researcher.

4. **Web Frontend (`/daily-predictions`)**:
   - Live dashboard featuring Hero Prediction Card, Directional Accuracy %, Intraday Target Hit Rate (30%), Brier Calibration stats, and active prompt variant tag.
   - **Historical Predictions Log & Prompt Inspector**: Expandable prediction rows with full quantitative rationale, market catalyst tags, Open/High/Low/Close prices, expected return %, confidence, and matched active system prompt text per prediction.
   - **Autoresearch & Prompt Evolution Arena**: Performance Ratchet Score dashboard with live formula breakdown, twice-weekly DeepSeek Flash Autoresearcher Meta-Prompt inspector, and prompt variant mutation history.

## Execution & Dispatch Architecture

1. **High-Precision Edge Cron Dispatcher (`apps/cron-dispatcher`)**:
   - Cloudflare Worker running 5 consolidated edge cron triggers (`0 13,18 * * MON-FRI`, `35 13-15 * * MON-FRI`, `15 21 * * MON-FRI`, `0 22 * * SUN,WED`).
   - Unified dispatcher routing to both `daily-predictor.yml` (Predictions, Evaluations, Autoresearch) and `ingest.yml` (Ingestion & Consensus).
   - Dispatches on-demand `workflow_dispatch` requests to GitHub's REST API using secure `GITHUB_PAT` credentials.
   - Bypasses GitHub Actions scheduled queue delays, launching workflows in < 5 seconds.

2. **Market-Open Safety Guardrail**:
   - Implemented in `.github/workflows/daily-predictor.yml`.
   - If a pre-market `daily-predictor` run is triggered or delayed after **9:30 AM EDT (13:30 UTC)**, the step automatically logs a warning and exits cleanly without recording stale intraday predictions.

## Database Schema

- `public.daily_predictions`: Stores predictions, actual Open/High/Low/Close prices, EOD correctness (`is_correct`), intraday target hit (`intraday_hit`), intraday direction hit (`intraday_direction_hit`), and Brier scores.
- `public.prompt_experiments`: Tracks `DAILY_PREDICTOR_PROMPT` variants, statuses, and performance metrics.

## Related

- [[entities/sector-predictor-arena]] — Sector predictor arena comparison
- [[entities/autoresearch]] — Portfolio auto-research subsystem
- [[entities/database]] — Core database schema and prompt tracking tables
