---
tags: [concept, daily-predictor, jev, risk-management, no-trade]
category: concept
---

# Confidence Gating (NO_TRADE)

Confidence gating lets a directional model refuse to trade when its own conviction is too low. It was introduced with the `jev-local-autoresearched` champion track, where the autoresearch loop co-evolves a `min_confidence` threshold alongside the decision criteria.

## Mechanism

`JevCriteriaConfig` (`apps/engine/local_autoresearch/manifest.py`) carries a `min_confidence` field bounded to `[50.0, 100.0]`. During a live prediction in `apps/engine/tasks/daily_predictor.py`:

```
raw_dir = Jev's chosen direction
if confidence < min_conf:
    pred_dir = 'NO_TRADE'
else:
    pred_dir = raw_dir
```

The raw decision and confidence are still recorded; only the stored `predicted_direction` is gated. The champion variant ships with a `61.0%` gate. The default curated seed uses `61.0%`, while the plain `~typesafe/jev-latest` baseline does not gate.

## Evaluation Semantics

In `apps/engine/tasks/evaluate_daily_predictions.py`, a `NO_TRADE` prediction is treated as *abstention*, not a wrong answer:

- `is_correct = None`
- `brier_score = None`
- `intraday_hit = None`
- `intraday_dir_hit = None`

Aggregate accuracy and Brier metrics therefore exclude gated days, so the model is neither rewarded nor punished for staying flat. Selectivity (the fraction of days actually traded) is tracked separately by `calculate_metrics()` in `jev_evaluator.py` as `selectivity_pct`.

## Rationale

Close-to-open returns are near 50/50, so forcing a directional bet on every session dilutes win rate and Sharpe. Gating preserves capital and win rate during ambiguous regimes while keeping the model exposed on high-conviction days. Because the threshold is a mutation lever, the meta-researcher can discover the trade-off empirically — the champion settled at a level that retained ~80% traded win rate.

## Presentation

The web arena surfaces the abstention state explicitly. `HeroPredictionCard.tsx` detects `predicted_direction === 'NO_TRADE'` (or zero confidence) and renders an amber `⚡ NO TRADE` label instead of the emerald/rose UP/DOWN coloring, and `computeDailyPredictionStats()` filters `NO_TRADE` rows out of the evaluated-accuracy calculation.

## Related

- [[entities/local-autoresearch]] — evolves the gate
- [[entities/daily-market-predictor]] — the arena that runs gated predictions
- [[concepts/locked-vault-kfold]] — sibling mutation lever
- [[concepts/jev-decisions-model]] — the decision model being gated
