---
tags: [autoresearch, evaluation, scoring, jev, directional]
category: concept
---

# Pure Directional Scoring

Pure Directional Scoring is the evaluation metric used by [[entities/local-autoresearch]] for categorical binary decision models like Jev System One. It replaces multi-metric equity ratchet formulas that rely on numerical price targets and expected return magnitudes.

## Motivation

Standard daily predictor models output explicit price targets (`target_price`) and magnitude expectations (`expected_return_pct`). Their evaluations compute:
- **`intraday_hit`**: Whether intraday high or low touched the predicted price target.
- **`magnitude_capture`**: Ratio of predicted price target to actual excursion.

Categorical decision models (like Jev System One on OpenRouter Alpha Decisions) output only binary direction (`UP` or `DOWN`) and calibrated probabilities (`{"UP": 0.65, "DOWN": 0.35}`). They do not emit target prices or return percentages.

In early implementations, evaluating Jev with the standard ratchet formula led to two distortions:
1. **Artificial Intraday Hit**: Using `(high > open)` for `UP` and `(low < open)` for `DOWN` resulted in a ~100% hit rate on the S&P 500, granting an unearned +35.0 free points.
2. **Ignored Confidence Gating**: Evaluating raw close accuracy across all days penalized selective models that intentionally filtered out low-conviction regimes (`NO_TRADE`).

## Formula

$$\text{Score} = (0.65 \times \text{Traded Win Rate}) + (0.25 \times \text{Close Accuracy}) + (0.10 \times \text{Selectivity}) - (\text{Mean Brier} \times 20.0)$$

### Metric Weights

- **Traded Win Rate (65% weight)**: Directional accuracy evaluated strictly on traded days ($\text{confidence} \ge \text{min\_confidence}$). Rewards disciplined gating. If a model trades 0 days, this is 0.0% (penalizing cowardice).
- **Close Accuracy (25% weight)**: Overall directional correctness across all historical sessions in the pool, ensuring baseline market intuition.
- **Selectivity (10% weight)**: Percentage of sessions traded ($\text{traded\_days} / \text{total\_days} \times 100$). Discourages extreme cherry-picking (such as trading only 2 days a year to report a 100% win rate).
- **Calibrated Brier Penalty ($\times 20.0$)**: Subtracted penalty for probabilistic miscalibration. A well-calibrated coin flip ($P=0.5$, Brier 0.25) incurs a 5.0 pt penalty.

## Benchmark Invariants

- **Uninformative Baseline**: A 50/50 coin flip model trading every day scores exactly **50.00** ($0.65 \times 50 + 0.25 \times 50 + 0.10 \times 100 - 0.25 \times 20 = 50.0$).
- **Statistical Edge**: A skilled model trading 60% of sessions with a 60% traded win rate, 55% overall accuracy, and 0.22 Brier scores **56.85**, clearing the overfit penalty hurdle cleanly.

## Known Limitations & The Selectivity Incentive Trap

As analyzed in [[concepts/daily-directional-predictability-limits]], the `+ 0.10 * Selectivity` term inadvertently subsidized over-trading:
- Models trading 100% of days received +10.0 free points, while models with disciplined confidence gates trading only 30% of high-conviction days suffered a -7.0 point penalty.
- This incentivized meta-researchers (like Qwen) to lower confidence thresholds and trade flat, random sessions, ultimately eroding out-of-sample accuracy on the [[concepts/regime-vault]].

## Related

- [[entities/local-autoresearch]] — the optimization loop consuming this metric
- [[concepts/daily-directional-predictability-limits]] — post-mortem on accuracy ceilings and the selectivity trap
- [[concepts/baseline-calibration]] — recalibration of baselines when moving datasets
- [[concepts/confidence-gating]] — gating mechanism enabling selective trading
- [[concepts/regime-vault]] — out-of-distribution stress testing
