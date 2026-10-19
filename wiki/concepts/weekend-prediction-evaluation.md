---
tags: [sector-predictor, evaluation, weekend, scheduling, timezone]
category: concept
---

# Weekend Prediction Evaluation

Weekend prediction evaluation is the scheduling rule that lets the sector-prediction evaluator score weekly predictions on Saturday and Sunday even though equity markets are closed. Weekly sector predictions that mature on a Monday (for example a 7-day target opened the prior Monday) have already completed their entire trading week at Friday's close, so they are mature and should be evaluated over the weekend rather than waiting for Monday's open.

## The Rule

The evaluator anchors "today" to Eastern Time (`EASTERN_TZ`) and then extends the maximum evaluation date forward when run on a weekend:

| Run day | `max_eval_date` |
|---------|-----------------|
| Sunday  | `today + 1 day` (Monday) |
| Saturday | `today + 2 days` (Monday) |
| Weekday | `today` |

Predictions are fetched with `target_date <= max_eval_date`, so a Sunday run picks up predictions maturing the following Monday. This keeps the evaluation cadence aligned with the trading week rather than the calendar week.

## Date Anchoring

Both the evaluator and the sector predictor accept an explicit date anchor for deterministic backfills and replays:

- `run_evaluation(force=..., date_anchor=...)` — overrides the computed "today"
- `run_sector_predictions(target_model=..., date_anchor=...)` — overrides the prediction date
- CLI flags: `--date YYYY-MM-DD` on both entry points, plus `--model` on the sector predictor to filter to a single model track

Anchoring the date makes historical re-runs reproducible and decouples the pipeline from wall-clock time, complementing the project's broader no-lookahead guarantees.

## Related

- [[entities/sector-predictor-arena]] — the arena these predictions belong to
- [[concepts/sector-model-tracks]] — per-model prediction tracks
- [[concepts/zero-lookahead-materialization]] — related determinism guarantees
