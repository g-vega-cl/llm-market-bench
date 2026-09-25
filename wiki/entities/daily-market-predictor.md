---
tags: [predictor, daily, intraday, sp500, autoresearch, deepseek, minimax, jev]
category: entity
---

# Daily S&P Market Predictor and Autoresearch Loop

The **Daily S&P Market Predictor** generates 9:15 AM ET pre-market predictions for intraday S&P 500 (SPY) price action, determining whether the 4:00 PM ET Close price will be higher (`UP`) or lower (`DOWN`) than the 9:30 AM ET Open price ($\text{Direction} = \text{UP if } \text{Close} \ge \text{Open} \text{ else DOWN}$).

## Key Features

1. **Pre-Market Inference (9:20 AM ET)**:
   - Command: `python main.py daily-predictor [--ticker SPY] [--force]`
   - **Trading Day and Holiday Validation**: Checks `MarketDataManager.is_trading_day()` against FMP exchange holidays (with rule-based fallback for US federal market holidays). Automatically exits without logging predictions on weekends or exchange holidays such as Labor Day, unless bypassed with `--force`.
   - **Pure Model Arena**: Runs **DeepSeek Flash** (`deepseek-v4-flash` via Instructor), **MiniMax-M3** (`MiniMax-M3` via MiniMax JSON client with explicit JSON schema footer), and **Jev** (`~typesafe/jev-latest` via OpenRouter Decisions API) in an isolated model arena, logging predictions independently for each model without reasoning cross-contamination.
     - Context: Synthesizes today's live morning economic releases (CPI, PPI, Jobs, Retail Sales prints with actual vs consensus surprises and release status via `get_today_economic_releases_summary()`), forward high-impact calendar scenarios (via `execute_get_calendar_scenario_analysis_tool(timeframe="tomorrow")`), dual AI Wall Street newsletter briefings (prior session `close` executive summary & key takeaways via `execute_fetch_daily_newsletter_tool(session="close", include_full_content=False)` plus today's full pre-market `open` briefing via `execute_fetch_daily_newsletter_tool(session="open", include_full_content=True)`), live pre-market price quotes & overnight gap metrics (via FMP `/quote` and `MarketDataManager.get_premarket_quote` across US indices `SPY`, `QQQ`, `DIA`, `IWM`, international proxies `EWJ`, `VGK`, Treasury yield proxies `TLT`, `IEF`, and commodities/FX `GLD`, `USO`, `UUP`), prior session regular trading hours intraday movement profile (OHLC, True Intraday Return %, CLV, Initial Balance breakout, and session archetype via `get_intraday_movement_report()`), technical indicators (SMA20, 5-day return), cross-asset macro options derivatives positioning & volatility skew (via `execute_get_macro_options_sentiment_tool(primary_ticker="SPY")` covering `SPY`, `QQQ`, `IWM`, and `GLD` with timestamp & session staleness metadata), and canonical tools context (`execute_get_global_macro_context_tool`, `execute_get_volatility_index_details_tool`, `execute_market_health_barometer_tool`, `execute_get_market_feeling_tool`).
   - **Zero-Mean Anti-Bias Mandate**: System prompt enforces a zero-mean distribution baseline (~50/50 UP vs DOWN) to eliminate pre-trained LLM long-term market drift bias. Requires strictly symmetric evaluation of bearish breakdown signals (VWAP resistance, RSI > 70 overbought exhaustion, yield surges) alongside bullish momentum signals.

2. **Post-Market Evaluation (5:15 PM EDT / 4:15 PM EST)**:
   - Command: `python main.py evaluate-daily-predictions [--target-date YYYY-MM-DD] [--force]`
   - **Active Session Guard**: Skips evaluation if the target date is today and the market session is still active (< 16:05 ET) to prevent premature evaluation against early intraday price snapshots.
   - **Non-Trading Day Purging**: If price data cannot be fetched and the target date was a non-trading day (weekend or market holiday), deletes the invalid prediction from `daily_predictions` to prevent indefinite retry loops.
   - Scopes today's 9:30 AM Open, High, Low, and 4:00 PM Close prices safely after market close by prioritizing timestamped Regular Trading Hours (`09:30:00 <= timestamp <= 16:00:00` ET) hourly bars (with automatic fallback to FMP `/historical-price-eod/full` EOD history). This guarantees zero extended-hours/post-market price contamination while immediately capturing afternoon price extremes.
   - Calculates **Directional Accuracy** (`is_correct`), **Intraday Target Hit Rate** (`intraday_hit`), **Intraday Direction Hit Rate** (`intraday_direction_hit`), and **Brier Calibration Score** ($\text{Brier} = (p - y)^2$, where $p = \text{confidence}/100.0$).
   - **System Portfolio Execution**: Automatically triggers mechanical 100% equity day trading execution for both portfolio tracks:
     - **Target-Exit Portfolios** (`sys-daily-spy-{model_name}`): 5 bps slippage, exits on intraday profit target hit or 3:30 PM time exit.
     - **3:50 Close-Exit Portfolios** (`sys-daily-spy-close-{model_name}`): 2 bps slippage (0.02%), ignores intraday profit target hits and holds position until 3:50 PM session close.
   - **Daily Post-Mortem Island (`analysis/daily_postmortem.py`)**:
     - Command: `python main.py daily-postmortem [--target-date YYYY-MM-DD] [--force]`
     - Triggered automatically upon completion of `evaluate_daily_predictions` when predictions are evaluated.
     - Conducted by **OpenAI Luna (`gpt-5.6-luna`)** with `instructor.Mode.JSON` and active reasoning (`reasoning_effort="medium"`).
     - Strict Anti-Hallucination Grounding: Dual-bookended between morning rationale/catalysts, verified 7-bar RTH hourly price tape, and the official 5:00 PM ET evening market close brief (`generated_newsletters`).
     - Closed Root-Cause Taxonomy: Categorizes outcomes into `ACCURATE_CAPTURE`, `TIMID_MAGNITUDE`, `OVERSHOT_TARGET`, `CATALYST_INVERSION`, `INTRADAY_REVERSAL`, `RANGEBOUND_CHOP`, or `UNFORESEEN_SHOCK`.
     - Persists directly on `daily_predictions` (`postmortem_category`, `postmortem_flawed_assumption`, `postmortem_lesson`, `was_predictable`, `postmortem_evaluated_at`).
     - If predictable and actionable (`was_predictable=True` and category != `ACCURATE_CAPTURE`), saves a memory in `memories` under `AUTORESEARCH_INSIGHT` (`scope='daily_predictor'`, `track_id=model_name`).
     - Feeds directly into Sunday `daily-autoresearch` via `compute_magnitude_postmortem_summary()`, allowing the weekly prompt evolution loop to compound verified causal lessons without daily recency bias.


3. **Weekly Prompt Evolution & Performance Ratchet (Sunday 6:00 PM ET / 10:00 PM UTC)**:
   - Command: `python main.py daily-autoresearch`
   - **Independent Multi-Model Tracks**: Evaluates recent predictions over the prior 7 days (all available trading sessions) and evolves system prompt variants independently for each participating model (`deepseek-v4-flash`, `MiniMax-M3`, and `~typesafe/jev-latest`), strictly scoped by `track_id` in `prompt_experiments`. Models never share or cross-pollinate prompt strategies or baselines.
   - **Single Active Variant Enforcement**: Deploying a new active variant for a model track automatically demotes all prior `active` variants for that `track_id` to `saved`, guaranteeing a single live active strategy per model track.
   - Combined Multi-Factor Ratchet Score formula:
     $$\text{Ratchet Score} = (0.55 \times \text{close\_accuracy\_pct}) + (0.35 \times \text{intraday\_hit\_pct}) + (0.10 \times \text{magnitude\_capture\_pct}) - (\text{mean\_brier} \times 50.0)$$
   - **Granular Metrics Persistence**: Persists full score factor breakdowns in `prompt_experiments.metrics` (`close_accuracy_pct`, `intraday_hit_pct`, `magnitude_capture_pct`, `mean_brier`, `predictions_evaluated`, `correct_count`, `intraday_hit_count`) for transparent audits.
   - **Magnitude Calibration Postmortem & Catalyst Enrichment**: Evaluates whether timid targets were set on large breakout/trend days ($\text{capture} = \min(1.0, |\text{expected\_return}| / \max(|\text{peak}|, |\text{close}|)) \times 100$, awarded only on successful target hits). The meta-researcher receives a detailed postmortem breakdown diagnosing timid sizing vs overshooting errors cross-referenced with 14 days of ingested newsletters, market events, and active thematic concepts from `concept_metrics` to evolve analytical catalyst recognition rules without compromising baseline target hit reliability.
   - Applies ratchet logic per model: if a model's recent 7-day performance beats its historical baseline, establishes a new baseline; if lower, reverts to baseline prompt content for mutation.
   - **Specialized Meta-Researchers**: Uses DeepSeek Flash (`deepseek-v4-flash`) to evolve strategy prompts for DeepSeek and MiniMax, and OpenAI Luna (`gpt-5.6-luna`) to evolve classification criteria (`criteria_up` and `criteria_down`) for Jev.
   - **Backtest Isolation**: Evaluated prediction queries explicitly filter out records with `backtest` in `prompt_variant_tag`, preventing simulated historical backtests from affecting live weekly prompt mutations or ratchet scores.

4. **Web Frontend (`/daily-predictions`)**:
   - **Independent Model Tabs**: Dedicated navigation tabs for **DeepSeek Flash**, **MiniMax M3**, and **Jev (TypeSafe)** (with dynamic prediction counts). Selecting a tab isolates overview metrics, latest hero forecast, prediction log table, and autoresearch history strictly to that model.
   - **Strict Live Forecast Isolation**: `fetchDailyPredictions` and `/daily-predictions` filter out simulated backtest predictions (`prompt_variant_tag` containing `backtest`). Directional accuracy, intraday target hit rates, Brier calibration, and tab prediction counts strictly evaluate live 9:15 AM ET forecasts without dilution from historical backtests.
   - **Dual Sub-Views**: Seamless toggle switch between **Predictions Log** (live forecasts, hero card, and evaluated accuracy table) and **Autoresearch & Benchmark History** (ratchet score progression, baseline threshold milestones, and prompt mutation lineage).
   - **Strict Track-Isolated Active Resolution**: In the Autoresearch view, shows active ratchet score, all-time best baseline score, score progression deltas ($\pm\Delta$ vs parent baseline), and an interactive master-detail variant browser with full mutated system prompt strategy text and mutation rationales. Prompt resolution strictly operates on the selected model's lineage, defaulting directly to inspecting the current active variant. Includes a dedicated **Current Active Prompt** milestone card and **`🟢 Active Runtime: <variant_tag>`** banner with explicit visual lineage status badges (`🟢 ACTIVE`, `🏆 BASELINE`, `❌ DISCARDED`, `📦 SAVED`) ensuring discarded mutations and fallback active variants are immediately obvious. Features a fluent layout that avoids explicit media query breakpoints and raw pixel dimensions. Uses proportional flex wrapping (`flex-wrap`, `basis-72`, `basis-96`, `flex-[3]`) to let sidebar and details sit side by side on wide containers and stack cleanly on compact viewports. Enforces overflow containment by assigning `min-w-0` to all containers, wrapping segmented prompt `<pre>` blocks with `whitespace-pre-wrap break-words`, applying `break-all` to snake_case variant tags and tool names, using rem-based auto-fit subgrids (`repeat(auto-fit, minmax(min(100%, 15rem), 1fr))`), and capping lineage selector height with `max-h-96 overflow-y-auto`.
   - **Interactive Score Calculation & Breakdown**: Renders an interactive score breakdown card (`DailyScoreBreakdown`) under the selected prompt experiment in the Autoresearch tab. Features a live arithmetic formula substitution bar, 4 weighted pillar metric tiles (Directional Accuracy 55%, Intraday Target Hit 35%, Magnitude Capture 10%, Brier Penalty 50.0×), evaluated sample window metadata, an automatic low-sample sensitivity notice ($N < 5$), and a collapsible scoring methodology and weights guide.
   - **Predictions Log & Prompt Inspector**: Expandable prediction rows with full quantitative rationale, market catalyst tags, Open/High/Low/Close prices, expected return %, confidence, and matched active system prompt text per prediction with dedicated active prompt badge in the overview metrics.
   - **Relocated Backtest Arena Navigation**: Direct 1-click link to Backtest Arena located on the right side of the model tabs bar.

## Execution & Dispatch Architecture

1. **High-Precision Edge Cron Dispatcher (`apps/cron-dispatcher`) & Chained Execution**:
   - Cloudflare Worker running 4 consolidated edge cron triggers (`12 13,14 * * MON-FRI`, `35 13-16 * * MON-FRI`, `30 19,20 * * MON-FRI`, `0 21,22 * * MON-FRI`), respecting Cloudflare Free plan's 5 cron trigger limit.
   - Unified dispatcher routing intraday market workflows: `generate-newsletter.yml` (9:12 AM & 5:00 PM ET) and `ingest.yml` (9:35 AM, 11:35 AM, 3:30 PM ET).
   - **Downstream Chaining**: `generate-newsletter.yml` automatically triggers `daily-predictor.yml` upon completion (`daily-predictor` after the 9:12 AM morning brief and `evaluate-daily-predictions` after the 5:00 PM close brief), eliminating race conditions and saving 2 edge triggers.
   - Dispatches on-demand `workflow_dispatch` requests to GitHub's REST API using secure `GITHUB_PAT` credentials without executing LLM code directly on the edge worker.
   - Bypasses GitHub Actions scheduled queue delays, launching workflows in < 5 seconds.
   - Decoupled from intraday trading workflows: `daily-autoresearch` runs weekly (Sunday 6:00 PM ET / 10:00 PM UTC) directly via native GitHub Actions schedule (`0 22 * * SUN` in `daily-predictor.yml`).

2. **Runner Environment & API Key Injection**:
   - `.github/workflows/daily-predictor.yml` provisions secrets for financial data (`FMP_API_KEY`, `FRED_API_KEY`, `MASSIVE_API_KEY`), database access (`SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`), and all participating models (`DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`).

3. **Market-Open and Schedule Guardrails**:
   - Implemented in `.github/workflows/daily-predictor.yml`.
   - **Direct Schedule Routing**: Native schedule events (`0 22 * * SUN`) route directly to `daily-autoresearch` without hour-dependent branching, ensuring runner queue delays cannot trigger `daily-predictor`.
   - If a pre-market `daily-predictor` run is triggered or delayed after **9:30 AM EDT (13:30 UTC)**, the step automatically logs a warning and exits cleanly without recording stale intraday predictions.


## Database Schema & Model Training Telemetry
 
- `public.daily_predictions`: Stores predictions, actual Open/High/Low/Close prices, EOD correctness (`is_correct`), intraday target hit (`intraday_hit`), intraday direction hit (`intraday_direction_hit`), Brier scores, and the complete pre-market input features text (`market_context`) passed into the model.
- `public.prompt_experiments`: Tracks `DAILY_PREDICTOR_PROMPT` variants, statuses, and performance metrics.
- **Dataset Exporter**: `apps/engine/scripts/export_daily_predictor_dataset.py` formats historical predictions and compiled market contexts directly into SFT (`train.jsonl`) or DPO preference pairs for model fine-tuning and offline evaluation.
 
## Related
 
- [[concepts/system-portfolios]], mechanical sector long/short and daily SPY portfolios
- [[entities/sector-predictor-arena]], Sector predictor arena comparison
- [[entities/autoresearch]], Portfolio auto-research subsystem
- [[entities/database]], Core database schema and prompt tracking tables
