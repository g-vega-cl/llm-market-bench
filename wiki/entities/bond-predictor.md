---
tags: [entity, engine, tasks, bond, tlt, predictor]
category: entity
---

# Bond Predictor (TLT)

`apps/engine/tasks/bond_predictor.py` is the systematic daily bond predictor that produces open-to-close direction forecasts for **TLT** (iShares 20+ Year Treasury Bond ETF, ~17-year duration). It is a vertical slice island mirroring the [[entities/daily-market-predictor]] for the equity index, but applies fixed-income mechanics: bond prices move inversely to Treasury yields, so falling yields imply TLT UP and rising yields imply TLT DOWN. High duration makes TLT sensitive to morning economic prints (CPI, PPI, NFP), Fed expectations, and Treasury auction dynamics.

## Prompt Architecture

The predictor enforces the tool-first convention ("Provide Tools, Don't Push Data"). The initial prompt built by `construct_lean_bond_prompt` injects only lean temporal context — target ticker, prediction date, the 09:30–16:00 ET session window, and the pre-market/overnight quote with gap vs previous close. It deliberately omits bulky context tables, yield-curve dumps, and pre-injected news.

## Models & Toolbox

Three arena members compete each morning:

- **`gpt-5.6-luna`** (OpenAI) — multi-turn autonomous tool loop via `predict_bond_with_reasoning_model`
- **`deepseek-v4-flash`** (DeepSeek) — multi-turn autonomous tool loop, thinking enabled during final extraction
- **`~typesafe/jev-latest`** (OpenRouter) — single-turn Decisions API (`predict_daily_with_jev`) fed a pre-compiled lean tool bundle (`compile_jev_bond_context`), assembled from the Treasury yield curve and today's economic releases

The curated `BOND_TOOLBOX` exposes these canonical tools to the tool-loop models:

- `get_treasury_yield_curve`
- `get_today_economic_releases`
- `get_yield_curve_regime`
- `get_macro_options_sentiment`
- `get_calendar_scenario_analysis`

For the tool-loop models, the final structured prediction is extracted with an instructor client against `DailyPredictionOutput`, yielding `predicted_direction`, `confidence`, `expected_return_pct`, `rationale`, and `catalysts`.

## Scheduling & Idempotency

`run_daily_bond_prediction` refuses to run after 09:30 ET or before 04:00 ET, skips non-trading days, and skips when predictions already exist for the target ticker/date unless `force=True`. Successful predictions are persisted to the `daily_predictions` table with `ticker='TLT'`, `status='pending'`, and a `prompt_variant_tag` of `pull-bond-{model}`. The CLI routes here via `main.py daily-predictor --ticker TLT`; `--ticker ALL` runs SPY and TLT in sequence.

## Web Presentation

TLT predictions are presented in the unified Daily Predictor interface (`apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx`, `/daily-predictions?ticker=TLT`). An asset segment toggle allows switching between S&P 500 (SPY) and 20+ Year Treasuries (TLT), dynamically rendering the bond arena models (`gpt-5.6-luna`, `deepseek-v4-flash`, `~typesafe/jev-latest`) with GPT-5.6 Luna selected as the default.

## Related

- [[entities/daily-market-predictor]] — the SPY equity sibling
- [[entities/daily-bond-trading]] — the execution consumer of these predictions
- [[entities/treasury-yield-curve-tool]] — the flagship data source
- [[concepts/system-portfolios]]
- [[concepts/daily-tlt-live-trading]]
- [[entities/tool-registry]]
