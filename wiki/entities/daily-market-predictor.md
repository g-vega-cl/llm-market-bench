---
tags: [predictor, daily, intraday, sp500, autoresearch, deepseek, minimax]
category: entity
---

# Daily S&P Market Predictor and Autoresearch Loop

The **Daily S&P Market Predictor** generates 9:15 AM ET pre-market predictions for intraday S&P 500 (SPY) price action, determining whether the 4:00 PM ET Close price will be higher (`UP`) or lower (`DOWN`) than the 9:30 AM ET Open price ($\text{Direction} = \text{UP if } \text{Close} \ge \text{Open} \text{ else DOWN}$).

## Key Features

1. **Pre-Market Inference (9:20 AM ET)**:
   - Command: `python main.py daily-predictor [--ticker SPY]`
   - **Pure Model Arena**: Runs **DeepSeek Flash** (`deepseek-v4-flash` via Instructor) and **MiniMax-M3** (`MiniMax-M3` via MiniMax JSON client with explicit JSON schema footer, 8,192 token ceiling, and YAML fallback parser) in an isolated model arena, logging predictions independently for each model without reasoning cross-contamination.
   - Context: Synthesizes the full AI Wall Street morning newsletter briefing (`execute_fetch_daily_newsletter_tool(session="open")`), live pre-market price quotes & overnight gap metrics (via FMP `/quote` and `MarketDataManager.get_premarket_quote` across US indices `SPY`, `QQQ`, `DIA`, `IWM`, international proxies `EWJ`, `VGK`, Treasury yield proxies `TLT`, `IEF`, and commodities/FX `GLD`, `USO`, `UUP`), technical indicators (SMA20, 5-day return), and canonical tools context (`execute_get_global_macro_context_tool`, `execute_get_volatility_index_details_tool`, `execute_market_health_barometer_tool`, `execute_get_market_feeling_tool`).
   - **Zero-Mean Anti-Bias Mandate**: System prompt enforces a zero-mean distribution baseline (~50/50 UP vs DOWN) to eliminate pre-trained LLM long-term market drift bias. Requires strictly symmetric evaluation of bearish breakdown signals (VWAP resistance, RSI > 70 overbought exhaustion, yield surges) alongside bullish momentum signals.

2. **Post-Market Evaluation (5:15 PM EDT / 4:15 PM EST)**:
   - Command: `python main.py evaluate-daily-predictions`
   - Scopes today's 9:30 AM Open, High, Low, and 4:00 PM Close prices safely after market close via FMP `MarketDataManager` (skips evaluation if target date hasn't closed yet).
   - Calculates **Directional Accuracy** (`is_correct`), **Intraday Target Hit Rate** (`intraday_hit`), **Intraday Direction Hit Rate** (`intraday_direction_hit`), and **Brier Calibration Score** ($\text{Brier} = (p - y)^2$, where $p = \text{confidence}/100.0$).
   - `intraday_hit` evaluates whether the stock reached or surpassed the predicted target return percentage (`expected_return_pct`) at any point between Open and Close (e.g. hitting +0.35% intraday high even if it closed at -0.20%).
   - **System Portfolio Execution**: Automatically triggers mechanical 100% equity day trading execution for each model's systematic portfolio (`sys-daily-spy-{model_name}`), logging trade records and updating portfolio equity/performance snapshots based on profit target hits or 3:30 PM time-based exits.

3. **Twice-Weekly Prompt Evolution & Performance Ratchet (Sun & Wed 6:00 PM ET)**:
   - Command: `python main.py daily-autoresearch`
   - **Independent Multi-Model Tracks**: Evaluates recent predictions and evolves system prompt variants independently for each participating model (`deepseek-v4-flash` and `MiniMax-M3`), strictly scoped by `track_id` in `prompt_experiments`. Models never share or cross-pollinate prompt strategies or baselines.
   - **Single Active Variant Enforcement**: Deploying a new active variant for a model track automatically demotes all prior `active` variants for that `track_id` to `saved`, guaranteeing a single live active strategy per model track.
   - Combined Multi-Factor Ratchet Score formula:
     $$\text{Ratchet Score} = (0.55 \times \text{close\_accuracy\_pct}) + (0.35 \times \text{intraday\_hit\_pct}) + (0.10 \times \text{magnitude\_capture\_pct}) - (\text{mean\_brier} \times 50.0)$$
   - **Granular Metrics Persistence**: Persists full score factor breakdowns in `prompt_experiments.metrics` (`close_accuracy_pct`, `intraday_hit_pct`, `magnitude_capture_pct`, `mean_brier`, `predictions_evaluated`, `correct_count`, `intraday_hit_count`) for transparent audits.
   - **Magnitude Calibration Postmortem & Catalyst Enrichment**: Evaluates whether timid targets were set on large breakout/trend days ($\text{capture} = \min(1.0, |\text{expected\_return}| / \max(|\text{peak}|, |\text{close}|)) \times 100$, awarded only on successful target hits). The meta-researcher receives a detailed postmortem breakdown diagnosing timid sizing vs overshooting errors cross-referenced with ingested newsletters, market events, and active thematic concepts from `concept_metrics` to evolve analytical catalyst recognition rules without compromising baseline target hit reliability.
   - Applies ratchet logic per model: if a model's recent performance beats its historical baseline, establishes a new baseline; if lower, reverts to baseline prompt.
   - Mutates mutable strategy section using DeepSeek Flash meta-researcher per model track.

4. **Web Frontend (`/daily-predictions`)**:
   - **Independent Model Tabs**: Dedicated navigation tabs for **DeepSeek Flash** and **MiniMax M3** (with dynamic prediction counts). Selecting a tab isolates overview metrics, latest hero forecast, prediction log table, and autoresearch history strictly to that model.
   - **Dual Sub-Views**: Seamless toggle switch between **Predictions Log** (live forecasts, hero card, and evaluated accuracy table) and **Autoresearch & Benchmark History** (ratchet score progression, baseline threshold milestones, and prompt mutation lineage).
   - **Strict Track-Isolated Active Resolution**: In the Autoresearch view, shows active ratchet score, all-time best baseline score, score progression deltas ($\pm\Delta$ vs parent baseline), and an interactive master-detail variant browser with full mutated system prompt strategy text and mutation rationales. Prompt resolution strictly operates on the selected model's lineage, defaulting directly to inspecting the current active variant. Includes a dedicated **Current Active Prompt** milestone card and **`🟢 Active Runtime: <variant_tag>`** banner with explicit visual lineage status badges (`🟢 ACTIVE`, `🏆 BASELINE`, `❌ DISCARDED`, `📦 SAVED`) ensuring discarded mutations and fallback active variants are immediately obvious. Features a responsive mobile-first layout that cleanly stacks the variant lineage selector above the prompt details inspector on mobile/tablet viewports and displays side-by-side on desktop (`lg:`).
   - **Interactive Score Calculation & Breakdown**: Renders an interactive score breakdown card (`DailyScoreBreakdown`) under the selected prompt experiment in the Autoresearch tab. Features a live arithmetic formula substitution bar, 4 weighted pillar metric tiles (Directional Accuracy 55%, Intraday Target Hit 35%, Magnitude Capture 10%, Brier Penalty 50.0×), evaluated sample window metadata, an automatic low-sample sensitivity notice ($N < 5$), and a collapsible scoring methodology and weights guide.
   - **Predictions Log & Prompt Inspector**: Expandable prediction rows with full quantitative rationale, market catalyst tags, Open/High/Low/Close prices, expected return %, confidence, and matched active system prompt text per prediction with dedicated active prompt badge in the overview metrics.
   - **Relocated Backtest Arena Navigation**: Direct 1-click link to Backtest Arena located on the right side of the model tabs bar.

## Execution & Dispatch Architecture

1. **High-Precision Edge Cron Dispatcher (`apps/cron-dispatcher`)**:
   - Cloudflare Worker running 5 consolidated edge cron triggers (`0 21,22 * * MON-FRI`, `35 13-16 * * MON-FRI`, `30 19,20 * * MON-FRI`, `15 13,14,21 * * MON-FRI`, `20 13,14 * * MON-FRI`).
   - Unified dispatcher routing intraday market workflows: `generate-newsletter.yml` (9:15 AM & 5:00 PM ET), `daily-predictor.yml` (9:20 AM prediction & 5:15 PM evaluation), and `ingest.yml` (9:35 AM, 11:35 AM, 3:30 PM ET).
   - Dispatches on-demand `workflow_dispatch` requests to GitHub's REST API using secure `GITHUB_PAT` credentials without executing LLM code directly on the edge worker.
   - Bypasses GitHub Actions scheduled queue delays, launching workflows in < 5 seconds.
   - Decoupled from weekend/midweek prompt optimization: `daily-autoresearch` runs 2x/week (Sun & Wed 6:00 PM ET) directly via native GitHub Actions schedule (`0 22 * * SUN,WED` in `daily-predictor.yml`).

2. **Runner Environment & API Key Injection**:
   - `.github/workflows/daily-predictor.yml` provisions secrets for financial data (`FMP_API_KEY`, `FRED_API_KEY`), database access (`SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`), and all participating models (`DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`).

3. **Market-Open Safety Guardrail**:
   - Implemented in `.github/workflows/daily-predictor.yml`.
   - If a pre-market `daily-predictor` run is triggered or delayed after **9:30 AM EDT (13:30 UTC)**, the step automatically logs a warning and exits cleanly without recording stale intraday predictions.

## Database Schema

- `public.daily_predictions`: Stores predictions, actual Open/High/Low/Close prices, EOD correctness (`is_correct`), intraday target hit (`intraday_hit`), intraday direction hit (`intraday_direction_hit`), and Brier scores.
- `public.prompt_experiments`: Tracks `DAILY_PREDICTOR_PROMPT` variants, statuses, and performance metrics.

## Related

- [[concepts/system-portfolios]] — mechanical sector long/short and daily SPY portfolios
- [[entities/sector-predictor-arena]] — Sector predictor arena comparison
- [[entities/autoresearch]] — Portfolio auto-research subsystem
- [[entities/database]] — Core database schema and prompt tracking tables
