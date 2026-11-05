---
tags: [calibration, evaluation, brier-score, confidence]
category: concept
---

# Brier Score & Confidence Calibration

The Brier score measures the accuracy of probabilistic predictions. In LLM Market Bench, sector predictions include a self-assessed confidence percentage. The Brier score quantifies calibration — how well confidence matches actual outcomes — and is retained as a stored diagnostic.

> [!IMPORTANT]
> Brier is no longer a scoring input. The `mean_brier × 50` accuracy penalty was replaced by [[concepts/conviction-points]] in November 2026. Brier remains stored on every prediction row for auditing, and `apps/engine/local_autoresearch/single_prompt_ratchet.py` still imports `calculate_brier_score` directly.

## Formula

For two-sided predictions (best and worst sectors):

$$
BS_{\text{best}} = (p - y_{\text{best}})^2, \quad y_{\text{best}} = 1.0 \text{ if } S_{\text{best}} \ge 50\% \text{ else } 0.0
$$

$$
BS_{\text{worst}} = (p - y_{\text{worst}})^2, \quad y_{\text{worst}} = 1.0 \text{ if } S_{\text{worst}} \ge 50\% \text{ else } 0.0
$$

$$
\text{Brier Score} = \frac{BS_{\text{best}} + BS_{\text{worst}}}{2}
$$

Where:
- $p$ = model confidence expressed as probability (0.0–1.0), with a fallback of 0.5 when confidence is missing
- $y_{\text{best}} = 1.0$ if the predicted best sector outperformed the median sector return, else 0.0
- $y_{\text{worst}} = 1.0$ if the predicted worst sector underperformed the median sector return (i.e. was in the bottom half of performers), else 0.0
- For legacy predictions without worst sector evaluations, Brier score falls back to single-sided $BS_{\text{best}}$.

Lower is better; 0.0 is perfect calibration.

## Usage in Sector Prediction Arena

- The `SECTOR_PREDICTOR_PROMPT` now requires the model to return a `confidence` float between 0.0 and 100.0.
- `SectorPredictionResponse` stores `confidence` with a default of 75.0 for backward compatibility.
- During evaluation, `calculate_sector_brier_score()` computes the Brier score and stores it in `sector_predictions.brier_score`.
- The web UI displays Confidence and Brier Score columns as diagnostics; conviction drives the composite score.

## Autoresearch Scoring (Superseded)

The predictor autoresearch weekly score previously read:

```
Score_weekly = Average(percentile_scores) - (Mean Brier × 50.0)
```

That term has been removed. It bounded confidence to roughly ±12 points on a 0–100 composite, which meant a model could win by ignoring calibration entirely. The current score is:

```
Score_weekly = 0.90 × accuracy_block + 0.10 × conviction_norm
```

where `accuracy_block` is the existing percentile/alpha composite and `conviction_norm` is the normalised [[concepts/conviction-points]] term. Brier is still written to `sector_predictions.brier_score` and shown as a diagnostic only.

Worst-sector legs are priced with the separate `worst_confidence` column. Legacy rows that never stated a worst-pick probability skip that leg rather than reusing the best-pick confidence.

## Related

- [[concepts/conviction-points]]
- [[entities/sector-predictor-arena]]
- [[concepts/auto-research-prompt-improver]]
- [[concepts/intraday-hit-metrics]]
