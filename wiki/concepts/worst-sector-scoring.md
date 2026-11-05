---
tags: [sector-predictor, evaluation, scoring, worst-sector, spy-alpha]
category: concept
---

# Worst Sector Scoring

The sector predictor now predicts both the single best performing sector and the single worst performing sector. This two-sided prediction improves the signal by forcing the LLM to identify both relative strength and weakness in the sector landscape, and the evaluation system rewards correct identification of the worst sector on the same percentile basis.

## Worst Sector Percentile Score

The worst sector prediction is scored by ranking its actual return against all other sectors in the universe:

$$
Score_{\text{worst}} = \frac{\text{Number of sectors with higher return}}{\text{Total sectors} - 1} \times 100
$$

- A perfect call (lowest return among all sectors) yields **100.0**.
- A worst call (highest return among all sectors) yields **0.0**.
- If the ticker is missing from the universe, the score defaults to **0.0**.

The function `calculate_worst_sector_percentile_score()` in `evaluate_predictions.py` implements this logic.

## S&P 500 Alpha Bonus

To reward absolute outperformance beyond relative ranking, a bonus is added to the composite score:

$$
\alpha = r_{\text{best sector}} - r_{\text{SPY}}
$$

Only positive alpha counts: `Bonus = max(0, α)`. This incentivises the model to not just pick the best sector but to pick one that actually beats the market.<br>(Data window: prediction start price to target date end price.)

## Composite Score

The final per-prediction score combines all three percentile components and the alpha bonus:

$$
\text{Base Score} = \text{Average}(S_{\text{best}}, S_{\text{worst}}, S_{\text{pair}})
$$

$$
\text{Score}_{\text{prediction}} = \text{Base Score} + \max(0, \alpha)
$$

If worst sector data is unavailable (historical predictions before the feature), the average only includes `S_best` and `S_pair`, maintaining backward compatibility.

## Ratchet Baseline Integration

The baseline ratchet in `predictor_autoresearch.py` uses this per-prediction score as the accuracy block and blends in conviction:

$$
\text{Ratchet Score} = 0.90 \times \text{Avg}(\text{Score}_{\text{prediction}}) + 0.10 \times \text{Conviction Score}
$$

The Brier score is still stored per prediction but is no longer deducted. The worst-sector leg is priced by its own `worst_confidence`; legacy rows without it skip that leg rather than reusing the best-pick probability. See [[concepts/conviction-points]].

All data is stored in the `sector_predictions` table (see [[entities/database]]) and displayed in the Sector Predictor Arena UI (see [[entities/sector-predictor-arena]]).

## Related

- [[entities/sector-predictor-arena]]
- [[concepts/brier-score]]
- [[concepts/auto-research-prompt-improver]]
