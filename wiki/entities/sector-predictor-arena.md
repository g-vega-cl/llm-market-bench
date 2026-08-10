---
tags: [web, ai-predictions, engine, ui]
category: entity
---

# AI Sector Predictor and Model Arena

The **AI Sector Predictor and Model Arena** is a forecasting and benchmarking system designed to predict weekly top-performing sectors and uncorrelated asset pairs for 7d, 30d, 60d, and 90d timeframes, while comparing the predictive accuracy across **DeepSeek Flash**, **MiniMax-M3**, **Gemini 3.5 Flash Lite**, and **GPT-5.6 Luna**.

---

## 🎯 Architecture & End-State Goals

### 1. Dynamic Reference Universe (Per-Week Isolation)
Rather than hardcoding a comparison universe of 14 sector ETFs, the evaluation engine determines the benchmark assets dynamically based on the week the prediction was made:
* For any prediction, the evaluator looks up the closest historical `correlation_runs` row by matching the `prediction_date`.
* The `tickers` array stored in that correlation run (which lists all 59+ system-tracked assets, including commodities, crypto, and equities) is used as the **reference comparison universe**.
* This aligns evaluation with what the model actually chose from, isolates comparison pools per prediction date, and eliminates dynamic universe leaks between runs.

### 2. Standardized Case-Insensitive Matching
* Both predictions and reference tickers are parsed and coerced to uppercase (via `.upper()`) before comparison.
* Lowercase model outputs (e.g. `["xlk", "xlv"]`) are parsed and correctly scored without causing silent evaluation skips.

### 3. Feedback-Driven Karpathy Ratchet
The Arena prompt evolution follows a strict feedback loop identical to the main investment engine:
1. **Weekly Evaluation**: The runner compiles all predictions with `target_date <= today` and marks them `evaluated`.
2. **Weekly Scoring**: A single `weekly_score` is computed as the average of the evaluated predictions' average scores:
   $$\text{Score}_{\text{prediction}} = \frac{\text{sector\_percentile} + \text{pair\_percentile}}{2}$$
   $$\text{Score}_{\text{weekly}} = \text{Average}(\text{Score}_{\text{prediction}})$$
3. **Database Metrics Tracking**: The `metrics` JSON column of the prompt variant that was active during that week is updated in `prompt_experiments` with `{"score": weekly_score}`.
4. **Ratchet Decision**:
   * The baseline score is calculated as the maximum score of any evaluated `SECTOR_PREDICTOR_PROMPT` variant in the database.
   * If the current week's score beats the baseline, a new baseline is established.
   * If it underperforms, the active prompt variant is reverted to the baseline variant (`revert_to_baseline()`) before mutating.
5. **Prompt Sandwich Architecture & Mutation Isolation**:
   * The sector predictor prompt is split into three sections: `SECTOR_PREDICTOR_CONSTRAINTS_HEADER` (role/context), `SECTOR_PREDICTOR_MUTABLE_STRATEGIES` (analytical instructions), and `SECTOR_PREDICTOR_CONSTRAINTS_FOOTER` (required JSON schema).
   * The meta-researcher mutates **only** the middle `MUTABLE_STRATEGIES` section. System header constraints and output format JSON schemas are automatically wrapped around the mutated strategy, preventing schema drift or format hallucinations.
   * Backward-compatible fallback (`split_predictor_prompt`) ensures historical monolithic variants are safely parsed without breaking baseline score comparisons.
6. **Mutation & Deployment**: The meta-researcher (Gemini) mutates the active strategy instructions to deploy the next week's prompt variant.

### 4. Robust Frontend Visuals & Audit Transparency
* **4-Model Scoreboard Grid**: Head-to-head scorecards dynamically calculate and display average percentile scores and top-quartile call rates across all 4 inference models (**DeepSeek Flash**, **MiniMax-M3**, **Gemini 3.5**, and **OpenAI GPT-5.6**).
* **Top Accuracy Chart & 4-Series Legend**: Historical accuracy trends render 4 distinct D3 color series (DeepSeek `#60a5fa`, MiniMax `#34d399`, Gemini `#f59e0b`, OpenAI `#a855f7`) at the top of the dashboard, supporting timeframe filters (`7d`, `30d`, `60d`, `90d`, `all`).
* **Interactive Predictions Data Table**: Includes a dedicated data table (`AIPredictionsTable.tsx`) for high-density tracking across all forecast horizons. Features sortable headers (Prediction Date, Target Date, Return, Alpha, Model, Percentile Score), search, filters (Model, Status, Horizon), dual-target display (Single Sector + Pair Combination), Alpha vs S&P 500 calculation, and expandable audit drawers.
* **S&P 500 Benchmark Window Returns**: Evaluated predictions display actual window returns (`predicted_sector_return`, `predicted_pair_return`, `benchmark_spy_return`) alongside outperformance vs the S&P 500 (SPY) benchmark (e.g. `+2.4% vs S&P 500`).
* **🔍 Data Audit & Price Verification**: Each evaluated outcome card/row renders an explicit price audit block (`evaluation_audit_data` JSONB) displaying starting prices, ending prices, percentage returns, and date windows for SPY, Sector ETF, and Pair ETFs so users can independently verify data accuracy.
* **Score Constituents Breakdown**: Each card explicitly exposes its 50/50 constituents (50% Sector Score, 50% Pair Score) and the composite formula $( \text{Sector Score} + \text{Pair Score} ) \div 2$ inline.
* **Timeframe Filters**: The dashboard allows filtering/splitting the chart by prediction horizon (e.g., viewing 7d, 30d, 60d, 90d individually) to prevent target date collisions and ensure statistical meaning.
* **Single Data Point Resilience**: The time scale domain adds a $\pm 1$-day margin when only a single data point is evaluated, preventing D3 coordinate scaling crashes.
* **Unified Metrics**: Summary card statistics and chart plotting use the same formula (averaging both sector and pair scores).
* **Tabbed View**: Features a tabbed layout separating the forecasting tracker (Arena Dashboard) from the prompt evolution and mutations tracker (Prompt Auto-Research).
* **Prompt Evolution Details**: Visualises baseline scores, active prompt details, formula breakdowns, and line diffs for mutated variants.

---

## 📁 Implementation Components

### Engine Tasks
* **Prediction Generation (`apps/engine/tasks/sector_predictor.py`)**: Runs prediction inference across DeepSeek Flash, Gemini 3.5 Flash Lite, and GPT-5.6 Luna (via instructor proxy) and MiniMax-M3 (via direct HTTP payload). Inserts predictions into `sector_predictions` table.
* **Auto-Research Evolution (`apps/engine/tasks/predictor_autoresearch.py`)**: Orchestrates the weekly prompt evolution, updates database metrics, applies the ratchet revert step, and mutates the system prompt using a hybrid async/sync completions handler to prevent runtime await crashes.
* **Inference Evaluation (`apps/engine/tasks/evaluate_predictions.py`)**: Computes percentile performance metrics against the corresponding weekly correlation run assets.

### Web Front-End
* **Route**: `apps/web/src/routes/ai-predictions/index.tsx` using `createServerFn` and TanStack Start to load both predictions and predictor experiments.
* **API Fetcher**: `apps/web/src/features/ai-predictions/api/fetch-predictions.ts` reading from `sector_predictions` (predictions) and `prompt_experiments` (scoped to `SECTOR_PREDICTOR_PROMPT` for experiments).
* **Data Table**: `apps/web/src/features/ai-predictions/components/AIPredictionsTable.tsx` providing interactive column sorting, search, filtering, view switching, and expandable audit drawers.
* **Visuals**: `apps/web/src/features/ai-predictions/components/AIPredictionChart.tsx` leveraging `d3` rendering pipeline.
* **Pages**: `apps/web/src/features/ai-predictions/pages/AIPredictionsPage.tsx` showing unified metrics, target track records, baseline stats, interactive prompt changes, and a detailed experiment history displaying active periods, mutation types, and parent references.

---

## Related
- [[entities/autoresearch]] — the parent autonomous prompt improvement engine
- [[entities/web-app]] — parent dashboard
- [[entities/database]] — details about Supabase database tables
