---
tags: [daily-predictor, postmortem, luna, evaluation, autoresearch]
category: entity
---

# Daily Post-Mortem Island

The **Daily Post-Mortem Island** (`apps/engine/analysis/daily_postmortem.py`) audits intraday S&P 500 (SPY) daily predictions after market close. It is the causal-diagnosis layer of the [[entities/daily-market-predictor]] pipeline: after a prediction is evaluated against the verified price tape, this island explains *why* the forecast succeeded or failed and distills a durable lesson that feeds the weekly prompt-evolution loop.

## Trigger & Command

- CLI: `python main.py daily-postmortem [--target-date YYYY-MM-DD] [--force]` (registered as `COMMAND_DAILY_POSTMORTEM`).
- Runs automatically at the end of `evaluate_daily_predictions` whenever at least one prediction was evaluated, passing the same `target_date` and `force` flag.
- When no `target_date` is supplied, it defaults to the most recent evaluated target date.
- Predictions that already carry a `postmortem_evaluated_at` timestamp are skipped unless `--force` is set.

## Grounding Inputs (Anti-Hallucination)

The diagnosis is strictly bookended by three verified sources, so the model cannot invent macro excuses:

1. **Morning prediction** — direction, confidence, target return, cited catalysts, and the original rationale.
2. **Verified RTH price tape** — hourly bars filtered to regular trading hours (09:30–16:00 ET) and rendered as an intraday path table.
3. **Evening market close brief** — the `session='close'` newsletter from `generated_newsletters` (title, summary, bullet points), with a fallback to the latest close brief if the date lookup misses.

The diagnosis is produced by **OpenAI Luna (`gpt-5.6-luna`)** via `instructor.Mode.JSON` with active reasoning (`reasoning_effort="medium"`), returning a structured `DailyPredictionDiagnosis`.

## Root-Cause Taxonomy

Every outcome is classified into a closed taxonomy (see [[concepts/daily-postmortem-taxonomy]]):

| Category | Meaning |
|---|---|
| `ACCURATE_CAPTURE` | Direction and magnitude hit cleanly |
| `TIMID_MAGNITUDE` | Correct direction, but target capped too low on a trend day |
| `OVERSHOT_TARGET` | Correct direction, but target exceeded session volatility |
| `CATALYST_INVERSION` | Morning catalyst occurred, but the market reacted opposite |
| `INTRADAY_REVERSAL` | Thesis worked early, then faded/reversed in the afternoon |
| `RANGEBOUND_CHOP` | Flat tape with no momentum; direction forced on chop |
| `UNFORESEEN_SHOCK` | Mid-day news/shock breaking after 9:30 AM |

Each diagnosis also records `was_predictable` (foreseeable from pre-market signals vs. random noise/breaking news), the `observed_driver`, the `flawed_assumption`, and a 1–2 sentence `actionable_lesson`.

## Persistence

Results are written directly onto the `daily_predictions` row:

- `postmortem_category`
- `postmortem_flawed_assumption`
- `postmortem_lesson`
- `was_predictable`
- `postmortem_evaluated_at`

These columns are added by the `20260925120000_add_daily_postmortem_fields.sql` migration.

## Memory & Autoresearch Feedback

When a diagnosis is both predictable and actionable (`was_predictable=True` and category is not `ACCURATE_CAPTURE`), the lesson is stored in `memories` as an `AUTORESEARCH_INSIGHT` (importance 8) with `scope='daily_predictor'` and `track_id=model_name`, using similarity checks to avoid duplicates.

The Sunday `daily-autoresearch` run consumes these via `compute_magnitude_postmortem_summary()`, which surfaces a **VERIFIED DAILY POST-MORTEMS & FAILURE DIAGNOSES (GPT-5.6 LUNA)** section and prefers the Luna category over its own heuristic diagnosis. This lets the weekly prompt-evolution loop compound verified causal lessons without daily recency bias. The exported predictor dataset (`export_daily_predictor_dataset.py`) also carries the post-mortem fields into SFT and DPO samples.

## Related

- [[entities/daily-market-predictor]] — the prediction pipeline this island audits
- [[entities/autoresearch]] — the weekly prompt-evolution loop that consumes the lessons
- [[concepts/daily-postmortem-taxonomy]] — the closed root-cause taxonomy
- [[concepts/hallucination-audit]] — grounding discipline shared across the platform
- [[entities/database]] — `daily_predictions` schema and migrations
