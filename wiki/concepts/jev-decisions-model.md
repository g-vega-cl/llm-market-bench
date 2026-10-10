---
tags: [jev, typesafe, openrouter, decisions-api, predictor, system-one, classifier, daily-predictor]
category: concept
---

# Jev Decisions Model

**Jev** (`~typesafe/jev-latest`, provider TypeSafe) is the fast *System One* probability classifier participating in the daily S&P market predictor arena. Unlike the generative predictors (DeepSeek Flash, MiniMax-M3) that emit free-form reasoning and are mutated as full strategy prompts, Jev classifies market state directly into `UP` / `DOWN` and returns calibrated probabilities through the **OpenRouter Decisions API**.

## Why It Is Different

Jev does not receive a natural-language strategy prompt. Instead, its behavior is fully determined by a pair of symmetric, human-readable **classification criteria** (`criteria_up`, `criteria_down`) that describe the technical/catalyst/macro conditions under which the market should be expected to close higher or lower. The question structure, choice labels (`UP`, `DOWN`), and instructions are **frozen** — only the criteria text is evolved.

## Architecture & Specs

- **Model ID**: `typesafe/jev-1.13` (tracked by alias `~typesafe/jev-latest`).
- **Context Length**: **32,000 tokens** across the `state` object and `questions`. Output decisions have zero token charge.
- **Primitives**: Jev natively supports three question primitives: `Choice` (multi-option selection with probability distribution), `Noul` (binary probability of a condition holding true), and `Score` (ordered scale with probability-weighted expectation).
- **Execution Surfaces**: Available via OpenRouter's Decisions API (`POST /api/alpha/decisions`) and System One API (`POST /api/v1/systemone`).

## Frozen Question Contract

The question shape is fixed in `apps/engine/core/llm/daily_predictor_prompts.py`:

- `JEV_PREDICTOR_QUESTION_KEY = "direction"`
- `JEV_PREDICTOR_QUESTION_TYPE = "choice"`
- `JEV_PREDICTOR_INSTRUCTIONS` — "Will SPY close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET vs the 9:30 AM ET Open?"
- `JEV_DEFAULT_CRITERIA` — baseline `UP` / `DOWN` criteria text.

Criteria are serialized to JSON via `format_jev_prompt_content()` and recovered via `parse_jev_prompt_content()` when stored in and read back from `prompt_experiments.prompt_content` (falling back to the defaults on missing/invalid JSON).

### Curated Manifest & Confidence Gating (`jev-local-autoresearched`)

For the evolved local champion track (`jev-local-autoresearched`), the criteria schema is extended via `format_jev_curated_prompt_content()` and `parse_jev_curated_prompt_content()` to package:
1. **Decision Criteria**: Symmetrical `UP` and `DOWN` conditions requiring observable pre-market gap confirmation ($\ge \pm 0.30\%$), proxy confirmation (`QQQ`), and prior-day VWAP/CLV structure.
2. **Confidence Gating (`min_confidence`)**: Lower bound threshold (e.g. $61.0\%$). Decisions where Jev's output confidence is below this threshold automatically gate to `⚡ NO TRADE` (`predicted_direction = 'NO_TRADE'`), preserving portfolio capital and win rate during ambiguous regimes.
3. **Data Manifest ("Box of Data")**: JSON manifest specifying curated information inputs compiled by `pack_daily_context()`, including narrative newsletters (`Sherwood News`, `Chartr`), macro proxies (`QQQ`, `IWM`), options positioning, and technical intraday profiles, while strictly pruning noise sources (`UUP`, market barometer, market feeling).

## Inference Path

`predict_daily_with_jev()` in `apps/engine/tasks/daily_predictor.py`:

1. Requires `OPENROUTER_API_KEY` (raises `ValueError` if unset).
2. `POST https://openrouter.ai/api/alpha/decisions` with a payload containing `model`, a `state` object (`ticker`, `market_context`), and a `questions.direction` block (`type: choice`, `instructions`, and the evolved `criteria`).
3. Parses `answers.direction` → `choice`, `confidence`, and `probabilities`, normalizing to a 0–100 confidence.
4. Returns a standard prediction record (`predicted_direction`, `confidence`, `expected_return_pct=0.0`, `rationale`, `catalysts=[]`) so it slots into the same arena logging and evaluation pipeline as the other models.

Because Jev returns a classification only, `expected_return_pct` is always `0.0`. Magnitude capture is not part of its output.

## Systematic portfolio execution

Because Jev is a direction-only classifier without a percentage target:
- **Close-exit portfolio (`sys-daily-spy-close-~typesafe/jev-latest`)**: Jev participates in the 3:50 PM session close trader. This strategy trades directional bias (`UP` or `DOWN`) and exits at session close with 2 bps slippage.
- **Target-exit portfolio exclusion (`sys-daily-spy-`)**: Jev is excluded from the intraday target-exit portfolio. Target-exit trading requires a positive expected return percentage. Running a target exit on a 0% return target produces immediate exits at open and incurs unnecessary friction.

## Autoresearch Integration

The daily predictor arena supports two distinct Jev optimization pathways:
1. **Weekly Remote Ratchet (`~typesafe/jev-latest`)**: Runs in `apps/engine/tasks/daily_autoresearch.py` using `gpt-5.6-luna` to mutate symmetric criteria.
2. **Local Meta-Researcher (`jev-local-autoresearched`)**: Runs offline in `apps/engine/local_autoresearch/` pairing local **Qwen via Strata** with **Jev System One**. Co-evolves criteria, confidence gating thresholds, and the curated data manifest across non-chronological weekly k-fold splits before promoting champion variants to Supabase.

## Frontend

`DailyPredictionsPage` exposes dedicated tabs for both Jev models:
- **Jev (TypeSafe)**: Baseline uncurated model.
- **Jev (Local Champion)**: Evolved model featuring the `CuratedManifestCard` detailing the active "Box of Data" configuration, and high-contrast amber badges (`⚡ NO TRADE`) when confidence falls below the gating threshold.

## Related

- [[entities/daily-market-predictor]] — the prediction arena Jev participates in
- [[entities/local-autoresearch]] — local offline prompt and manifest evolution loop
- [[concepts/unified-daily-predictor]] — web interface hosting the multi-model prediction arena
- [[concepts/multi-track-autoresearch]] — per-model isolated prompt/criteria optimization
- [[concepts/prompt-section-splitting]] — standard prompt structure Jev bypasses
- [[entities/database]] — `prompt_experiments` stores the Jev criteria content

