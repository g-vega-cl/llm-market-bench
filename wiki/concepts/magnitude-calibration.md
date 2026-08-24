---
tags: [scoring, calibration, prediction, meta-researcher]
category: concept
---

# Magnitude Calibration

Magnitude Calibration measures how well the Daily S&P Market Predictor converts conviction into appropriately sized expected_return_pct values. It penalizes both timid underestimation (missing large moves) and overshooting (setting targets beyond available volatility) to improve overall prediction quality.

## Magnitude Capture Ratio

The core metric is the **magnitude capture ratio**, computed per prediction as:

$$
\text{Capture\%} = \min\left(1.0, \frac{|\text{expected\_return}|}{\max(|\text{peak}|, |\text{close}|)}\right) \times 100
$$

- Only awarded on predictions that are both directionally correct (`is_correct = True`) and hit the intraday target (`intraday_hit = True`).
- `expected_return` is the LLM's predicted magnitude (e.g., +0.20%).
- `peak` is the maximum favorable intraday excursion (high for UP, low for DOWN).
- `close` is the EOD absolute return.
- A prediction that captures 100% of the actual move scores 100; one that captures only 20% scores 20.

## Ratchet Score Integration

The ratchet scoring formula used for prompt mutation now includes magnitude capture as a third weighted factor:

$$
\text{Ratchet Score} = (0.55 \times \text{close\_accuracy\_pct}) + (0.35 \times \text{intraday\_hit\_pct}) + (0.10 \times \text{magnitude\_capture\_pct}) - (\text{mean\_brier} \times 50.0)
$$

- Directional accuracy weight reduced from 0.60 to **0.55**.
- Intraday hit rate weight reduced from 0.40 to **0.35**.
- Magnitude capture added at **0.10** weight.

## Postmortem Diagnosis & Catalyst Context

The meta-researcher receives an event-enriched `compute_magnitude_postmortem_summary()` Markdown table before each mutation cycle, cross-referencing prediction results with that day's newsletters and market events:

| Date | Dir | Pred % | Peak % | Close % | Correct? | Hit? | Brier | Capture % | Diagnosis | Key Catalysts / News |
|---|---|---|---|---|---|---|---|---|---|---|

Key diagnoses:
- **Timid / Underestimated**: Correct predictions where actual move ≥ 0.60% but capture < 40% — the LLM left momentum on the table. Postmortem context provides the specific news/catalysts (e.g. rate announcements or earnings surprises) driving the breakout move.
- **Overshot / Missed Target**: Correct direction but failed to hit target because `expected_return` **≥ 0.60%** was too aggressive for the actual intraday range.
- **Well-Calibrated**: Correct and on target with reasonable magnitude.
- **Wrong Direction**: Prediction was directionally incorrect.

Additionally, active thematic concept clusters and their velocity metrics from `concept_metrics` are appended to provide structural playbook context to the meta-researcher.

## Mutation Rules

The meta-researcher prompt now includes explicit magnitude calibration objectives:

1. Directional Accuracy (55%) and Intraday Hit Rate (35%) remain primary.
2. Magnitude Calibration (10%): "When high-impact catalysts or strong trend conditions align, instruct the predictor to be more confident and aggressive… instead of timid +0.20%."
3. **On rangebound or high-VIX days**, keep expected_return_pct conservative to ensure target hit reliability.

## Related

- [[entities/daily-market-predictor]]
- [[entities/daily-predictor-backtest-arena]]
- [[concepts/brier-score]]
- [[concepts/intraday-hit-metrics]]
- [[concepts/auto-research-prompt-improver]]
