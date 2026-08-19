---
tags: [calibration, evaluation, brier-score, confidence]
category: concept
---

# Brier Score & Confidence Calibration

The Brier score measures the accuracy of probabilistic predictions. In LLM Market Bench, sector predictions now include a self-assessed confidence percentage. The Brier score quantifies calibration — how well confidence matches actual outcomes — and is used as a penalty term in the autoresearch baseline score.

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
- The web UI displays Confidence and Brier Score columns in the AI Predictions table.

## Autoresearch Baseline Penalty

The predictor autoresearch weekly score is now:
Score_weekly = Average(percentile_scores) - (Mean Brier × 50.0)

The penalty encourages models to be well-calibrated, not just accurate. Legacy predictions without a Brier score contribute no penalty.

## Related

- [[entities/sector-predictor-arena]]
- [[concepts/auto-research-prompt-improver]]
- [[concepts/intraday-hit-metrics]]
