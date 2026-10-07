---
tags: [earnings, predictor, arena, luna, deepseek, jev, brier-score, engine]
category: entity
---

# Earnings Predictor Arena

The Day-1 Earnings Movement Predictor Arena benchmarks large language models on predicting intraday price reactions (UP vs DOWN from 9:30 AM Open to 16:00 Close ET) for corporate earnings announcements.

## Financial Formulation

Rather than predicting quarterly penny EPS or illiquid overnight gap-ups, the arena isolates post-announcement price discovery:

$$\text{Actual Direction} = \begin{cases} \text{UP} & \text{if } \text{close\_price} \ge \text{open\_price} \\ \text{DOWN} & \text{if } \text{close\_price} < \text{open\_price} \end{cases}$$

Calibration is scored using the Brier score:

$$\text{Brier Score} = \left(\frac{\text{Confidence}}{100.0} - (\text{Actual Direction} == \text{Predicted Direction})\right)^2$$

## Participating Models

The arena pits three models against one another:

1. **GPT Luna (`gpt-5.6-luna`)** — Evaluates deep multi-factor fundamental quality, full-year forward guidance tone, and pre-announcement momentum run-up via `apps/engine/core/llm/clients.py`.
2. **DeepSeek Flash (`deepseek-chat`)** — Lean, ultra-fast quantitative reasoning focused on SUE deciles and operating margin surprises.
3. **TypeSafe Jev (`~typesafe/jev-latest`)** — Fast System-One decision classifier operating via the OpenRouter Decisions API (`POST /api/alpha/decisions`), evaluating structured choice questions against frozen criteria.

## Pipeline & Execution

- **Prediction Task**: `apps/engine/tasks/earnings_predictor.py` runs pre-market (9:15 AM ET), discovers reporting candidates from `earnings_alpha_snapshots`, formats dense financial context, queries models, and upserts into `earnings_predictions`.
- **Evaluation Task**: `apps/engine/tasks/evaluate_earnings_predictions.py` runs post-market (16:05 ET), fetches RTH Open and Close prices, computes hit status and Brier score, and updates records.
- **CLI Commands**: `python main.py earnings-predictor` and `python main.py evaluate-earnings-predictions`.
- **Piggybacking**: Triggered in `.github/workflows/daily-predictor.yml` alongside daily market sessions.

## Related

- [[entities/earnings-alpha]]
- [[entities/earnings-audit]]
- [[concepts/earnings-prediction-strategies]]
- [[concepts/jev-decisions-model]]
- [[concepts/transparency-standard]]
