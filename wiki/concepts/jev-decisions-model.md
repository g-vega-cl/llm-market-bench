---
tags: [jev, typesafe, openrouter, decisions-api, predictor, system-one, classifier, daily-predictor]
category: concept
---

# Jev Decisions Model

**Jev** (`~typesafe/jev-latest`, provider TypeSafe) is the fast *System One* probability classifier participating in the daily S&P market predictor arena. Unlike the generative predictors (DeepSeek Flash, MiniMax-M3) that emit free-form reasoning and are mutated as full strategy prompts, Jev classifies market state directly into `UP` / `DOWN` and returns calibrated probabilities through the **OpenRouter Decisions API**.

## Why It Is Different

Jev does not receive a natural-language strategy prompt. Instead, its behavior is fully determined by a pair of symmetric, human-readable **classification criteria** (`criteria_up`, `criteria_down`) that describe the technical/catalyst/macro conditions under which the market should be expected to close higher or lower. The question structure, choice labels (`UP`, `DOWN`), and instructions are **frozen** — only the criteria text is evolved.

## Frozen Question Contract

The question shape is fixed in `apps/engine/core/llm/daily_predictor_prompts.py`:

- `JEV_PREDICTOR_QUESTION_KEY = "direction"`
- `JEV_PREDICTOR_QUESTION_TYPE = "choice"`
- `JEV_PREDICTOR_INSTRUCTIONS` — "Will SPY close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET vs the 9:30 AM ET Open?"
- `JEV_DEFAULT_CRITERIA` — baseline `UP` / `DOWN` criteria text.

Criteria are serialized to JSON via `format_jev_prompt_content()` and recovered via `parse_jev_prompt_content()` when stored in and read back from `prompt_experiments.prompt_content` (falling back to the defaults on missing/invalid JSON).

## Inference Path

`predict_daily_with_jev()` in `apps/engine/tasks/daily_predictor.py`:

1. Requires `OPENROUTER_API_KEY` (raises `ValueError` if unset).
2. `POST https://openrouter.ai/api/alpha/decisions` with a payload containing `model`, a `state` object (`ticker`, `market_context`), and a `questions.direction` block (`type: choice`, `instructions`, and the evolved `criteria`).
3. Parses `answers.direction` → `choice`, `confidence`, and `probabilities`, normalizing to a 0–100 confidence.
4. Returns a standard prediction record (`predicted_direction`, `confidence`, `expected_return_pct=0.0`, `rationale`, `catalysts=[]`) so it slots into the same arena logging and evaluation pipeline as the other models.

Because Jev returns a classification only, `expected_return_pct` is always `0.0` — magnitude capture is by design not part of its output.

## Autoresearch Integration

The weekly ratchet optimizer treats Jev as a third independent track (`concepts/multi-track-autoresearch`). `run_daily_autoresearch()` now iterates over `deepseek-v4-flash`, `MiniMax-M3`, and `~typesafe/jev-latest`. When the track is Jev (`"jev" in model_name.lower()`), mutation is delegated to `generate_new_jev_criteria()` rather than the standard prompt mutator:

- Uses **OpenAI Luna** (`gpt-5.6-luna` via `get_openai_client()`) as the meta-researcher, returning a structured `JevMetaCriteriaResponse` (`criteria_up`, `criteria_down`, optional `research_insight`).
- The meta-prompt freezes the question structure and instructs Luna to keep both criteria symmetric and to avoid bullish drift.
- The active prompt variant for a Jev track stores the JSON criteria (not a strategy prompt) and records `selected_tools = ["openrouter_decisions"]`.
- A Jev cold-start reset (1-in-6 stochastic exploration) discards prior criteria and generates fresh rules from scratch.

## Frontend

`DailyPredictionsPage` exposes a dedicated **Jev (TypeSafe)** tab (matched by `"jev"` in the model name) that isolates Jev's predictions, metrics, and evolved criteria alongside the DeepSeek and MiniMax tabs.

## Related

- [[entities/daily-market-predictor]] — the prediction arena Jev participates in
- [[concepts/multi-track-autoresearch]] — per-model isolated prompt/criteria optimization
- [[concepts/prompt-section-splitting]] — standard prompt structure Jev bypasses
- [[entities/database]] — `prompt_experiments` stores the Jev criteria content
