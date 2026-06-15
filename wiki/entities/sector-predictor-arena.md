---
tags: [web, ai-predictions, engine, ui]
category: entity
---

# AI Sector Predictor and Model Arena

The **AI Sector Predictor and Model Arena** is a standalone forecasting and benchmarking system designed to predict weekly top-performing sectors and uncorrelated sector pairs for 7d, 30d, 60d, and 90d timeframes, while comparing the predictive accuracy of **DeepSeek Flash** vs. **MiniMax-M3**.

## Features
- **AIPredictionsPage**: The web route (`/ai-predictions`) showcasing average performance comparison between DeepSeek Flash and MiniMax-M3, alongside a detailed feed of recent predictions, logic reasoning, and target timelines.
- **Custom D3 Line Chart**: Visualizes historical performance trends over time using native D3 scales, grids, ticks, and legend mapping, ensuring zero external charting library bloat.
- **Percentile-Based Scoring**: Evaluates predictions by converting raw performance returns into percentile rankings against all available sectors/sector pairs (0.0 to 100.0 scale).
- **Strict Isolation**: Keeps prompts, database rows, and autoresearch operations completely decoupled from the main investment engine via a custom prompt tag (`SECTOR_PREDICTOR_PROMPT`).

## Implementation

### Engine Tasks
- **Prediction Generation (`apps/engine/tasks/sector_predictor.py`)**: Runs prediction inference for DeepSeek (via instructor proxy) and MiniMax (via direct HTTP payload). Inserts predictions into `sector_predictions` table.
- **Auto-Research Evolution (`apps/engine/tasks/predictor_autoresearch.py`)**: A dedicated meta-researcher loop utilizing the Gemini client. Automatically mutates `SECTOR_PREDICTOR_PROMPT` and saves prompt variants in `prompt_experiments` under the isolated prompt name `SECTOR_PREDICTOR_PROMPT`.
- **Inference Evaluation (`apps/engine/tasks/evaluate_predictions.py`)**: Computes percentile performance metrics for single sectors and uncorrelated pairs on target dates.

### Web Front-End
- **Route**: `apps/web/src/routes/ai-predictions/index.tsx` using `createServerFn` and TanStack Start.
- **API Fetcher**: `apps/web/src/features/ai-predictions/api/fetch-predictions.ts` reading from `sector_predictions` table.
- **Visuals**: `apps/web/src/features/ai-predictions/components/AIPredictionChart.tsx` leveraging `d3` rendering pipeline.

## Production Schedule & Robustness

### GitHub Actions Workflow
The system is automated via the GitHub Actions workflow [.github/workflows/sector-predictions.yml](file:///home/cv/Documents/Code/llm-market-bench/.github/workflows/sector-predictions.yml).
- **Trigger**: Run weekly on a cron schedule at **Sunday 9:00 PM UTC** (5:00 PM ET).
- **Steps**: Configures a Python 3.12 environment, installs requirements, executes `predictor_autoresearch.py` to evaluate the past week's predictions and update the prompt, and then executes `sector_predictor.py` to generate the new week's predictions.

### MiniMax-M3 API Robustness
MiniMax-M3 leverages long-form internal reasoning (`reasoning_content`) which can occasionally exhaust API token limits, resulting in incomplete responses or empty payloads.
- **Retry Mechanism**: The prediction task implements a **3-attempt retry loop with a 2-second exponential backoff** for each timeframe.
- **Prompt Mutation on Retry**: If a MiniMax request fails on the first attempt, the subsequent attempts append a strict conciseness instruction (`Note: Keep your internal reasoning/thinking process concise to avoid token limit truncation`) to guarantee successful JSON payload generation.


## Database Schema (`sector_predictions`)
Stores historical prediction records:
- `id` (uuid, primary key)
- `prediction_date` (timestamp)
- `target_date` (timestamp)
- `timeframe` (text)
- `model_name` (text)
- `prompt_tag` (text)
- `predicted_sector` (text)
- `predicted_pair` (text[])
- `reasoning` (text)
- `sector_percentile_score` (numeric, nullable)
- `pair_percentile_score` (numeric, nullable)
- `status` (prediction_status: 'pending', 'evaluated')

## Related
- [[entities/autoresearch]] — the parent autonomous prompt improvement engine
- [[entities/web-app]] — parent dashboard
- [[entities/database]] — details about Supabase database tables
