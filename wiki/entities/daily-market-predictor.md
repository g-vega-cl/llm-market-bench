---
tags: [predictor, daily, intraday, sp500, autoresearch, deepseek, minimax]
category: entity
---

# Daily S&P Market Predictor and Autoresearch Loop

The **Daily S&P Market Predictor** generates 9:15 AM ET pre-market predictions for intraday S&P 500 (SPY) price action, determining whether the 4:00 PM ET Close price will be higher (`UP`) or lower (`DOWN`) than the 9:30 AM ET Open price ($\text{Direction} = \text{UP if } \text{Close} \ge \text{Open} \text{ else DOWN}$).

## Key Features

1. **Pre-Market Inference (9:15 AM ET)**:
   - Command: `python main.py daily-predictor [--ticker SPY]`
   - **Pure Model Arena**: Runs **DeepSeek Flash** (`deepseek-v4-flash` via Instructor) and **MiniMax-M3** (`MiniMax-M3` via MiniMax JSON client) in an isolated model arena, logging predictions independently for each model without reasoning cross-contamination.
   - Context: Synthesizes live pre-market price quote & overnight gap metrics (via FMP `MarketDataManager.get_premarket_quote`) positioned at the very top of context before technical indicators (SMA20, 5-day return) and canonical tools context (`execute_get_global_macro_context_tool`, `execute_get_volatility_index_details_tool`, `execute_market_health_barometer_tool`, `execute_get_market_feeling_tool`).
   - **Zero-Mean Anti-Bias Mandate**: System prompt enforces a zero-mean distribution baseline (~50/50 UP vs DOWN) to eliminate pre-trained LLM long-term market drift bias. Requires strictly symmetric evaluation of bearish breakdown signals (VWAP resistance, RSI > 70 overbought exhaustion, yield surges) alongside bullish momentum signals.

2. **Post-Market Evaluation (5:15 PM EDT / 4:15 PM EST)**:
   - Command: `python main.py evaluate-daily-predictions`
   - Scopes today's 9:30 AM Open, High, Low, and 4:00 PM Close prices safely after market close via FMP `MarketDataManager` (skips evaluation if target date hasn't closed yet).
   - Calculates **Directional Accuracy** (`is_correct`), **Intraday Target Hit Rate** (`intraday_hit`), **Intraday Direction Hit Rate** (`intraday_direction_hit`), and **Brier Calibration Score** ($\text{Brier} = (p - y)^2$, where $p = \text{confidence}/100.0$).
   - `intraday_hit` evaluates whether the stock reached or surpassed the predicted target return percentage (`expected_return_pct`) at any point between Open and Close (e.g. hitting +0.35% intraday high even if it closed at -0.20%).

3. **Twice-Weekly Prompt Evolution & Performance Ratchet (Sun & Wed 6:00 PM ET)**:
   - Command: `python main.py daily-autoresearch`
   - **Independent Multi-Model Tracks**: Evaluates recent predictions and evolves system prompt variants independently for each participating model (`deepseek-v4-flash` and `MiniMax-M3`), scoped by `track_id` in `prompt_experiments`.
   - Combined Multi-Factor Ratchet Score formula:
     $$\text{Ratchet Score} = (0.55 \times \text{close\_accuracy\_pct}) + (0.35 \times \text{intraday\_hit\_pct}) + (0.10 \times \text{magnitude\_capture\_pct}) - (\text{mean\_brier} \times 50.0)$$
   - **Magnitude Calibration Postmortem**: Evaluates whether timid targets were set on large breakout/trend days ($\text{capture} = \min(1.0, |\text{expected\_return}| / \max(|\text{peak}|, |\text{close}|)) \times 100$, awarded only on successful target hits). The meta-researcher receives a detailed postmortem breakdown diagnosing timid sizing vs overshooting errors to evolve analytical catalyst recognition rules without compromising baseline target hit reliability.
   - Applies ratchet logic per model: if a model's recent performance beats its historical baseline, establishes a new baseline; if lower, reverts to baseline prompt.
   - Mutates mutable strategy section using DeepSeek Flash meta-researcher per model track.

4. **Web Frontend (`/daily-predictions`)**:
   - **Independent Model Tabs**: Dedicated navigation tabs for **DeepSeek Flash** and **MiniMax M3** (with dynamic prediction counts). Selecting a tab isolates overview metrics, latest hero forecast, and prediction log table strictly to that model.
   - **Metrics Overview & Hero Card**: Scoped Directional Accuracy %, Intraday Target Hit Rate (40%), Brier Calibration stats, and active prompt variant badge.
   - **Predictions Log & Prompt Inspector**: Expandable prediction rows with full quantitative rationale, market catalyst tags, Open/High/Low/Close prices, expected return %, confidence, and matched active system prompt text per prediction.
   - **Relocated Backtest Arena Navigation**: Direct 1-click link to Backtest Arena located on the right side of the model tabs bar.

## Execution & Dispatch Architecture

1. **High-Precision Edge Cron Dispatcher (`apps/cron-dispatcher`)**:
   - Cloudflare Worker running 5 consolidated edge cron triggers (`0 13,18 * * MON-FRI`, `35 13-15 * * MON-FRI`, `15 21 * * MON-FRI`, `0 22 * * SUN,WED`).
   - Unified dispatcher routing to both `daily-predictor.yml` (Predictions, Evaluations, Autoresearch) and `ingest.yml` (Ingestion & Consensus).
   - Dispatches on-demand `workflow_dispatch` requests to GitHub's REST API using secure `GITHUB_PAT` credentials without executing LLM code directly on the edge worker.
   - Bypasses GitHub Actions scheduled queue delays, launching workflows in < 5 seconds.

2. **Runner Environment & API Key Injection**:
   - `.github/workflows/daily-predictor.yml` provisions secrets for all participating models (`DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) and database credentials (`SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`).

3. **Market-Open Safety Guardrail**:
   - Implemented in `.github/workflows/daily-predictor.yml`.
   - If a pre-market `daily-predictor` run is triggered or delayed after **9:30 AM EDT (13:30 UTC)**, the step automatically logs a warning and exits cleanly without recording stale intraday predictions.

## Database Schema

- `public.daily_predictions`: Stores predictions, actual Open/High/Low/Close prices, EOD correctness (`is_correct`), intraday target hit (`intraday_hit`), intraday direction hit (`intraday_direction_hit`), and Brier scores.
- `public.prompt_experiments`: Tracks `DAILY_PREDICTOR_PROMPT` variants, statuses, and performance metrics.

## Related

- [[entities/sector-predictor-arena]] — Sector predictor arena comparison
- [[entities/autoresearch]] — Portfolio auto-research subsystem
- [[entities/database]] — Core database schema and prompt tracking tables
