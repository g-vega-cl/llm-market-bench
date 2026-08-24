---
tags: [daily-predictions, score-breakdown, ui-component]
category: entity
---

# Daily Score Breakdown

An interactive React component (`DailyScoreBreakdown`) that renders a detailed, transparent calculation of the Daily Ratchet Score for a given prompt experiment. It displays the weighted formula substitution, four pillar metric tiles, sample window metadata, low-sample sensitivity warnings, and a collapsible scoring methodology guide.

## Purpose

Provides full auditability of the ratchet score computation directly in the Autoresearch & Benchmark History tab of the Daily Predictions page. Users can see exactly how each factor (directional accuracy, intraday hit rate, magnitude capture, Brier penalty) contributes to the final score, with live arithmetic substitution and per-pillar point contributions.

## Key Features

- **Formula Substitution Bar**: Shows the live arithmetic formula with color-coded factors and computed intermediate values.
- **4 Weighted Pillar Metric Tiles**:
  - EOD Directional Accuracy (55%) — green tile with correct/total count
  - Intraday Target Hit Rate (35%) — teal tile with targets hit/total count
  - Magnitude Capture Ratio (10%) — purple tile with breakout capture ratio
  - Brier Calibration Penalty (50.0×) — red tile with confidence calibration error
- **Low Sample Window Notice**: Automatically displayed when $N < 5$, explaining the sensitivity of short evaluation windows.
- **Collapsible Scoring Guide**: Explains the methodology behind each of the four factors.
- **Fallback Resolution**: If the experiment has enriched metrics (`close_accuracy_pct`, `intraday_hit_pct`, etc.), uses them directly. Otherwise, computes metrics from the provided `DailyPrediction[]` array, or falls back to a minimal score-only display.

## Usage

```tsx
<DailyScoreBreakdown experiment={experiment} predictions={predictions} />
```

- `experiment`: A `PromptExperiment` object with optional enriched `metrics`.
- `predictions` (optional): An array of `DailyPrediction` objects used for fallback computation.

## Related

- [[entities/daily-market-predictor]] — The parent feature that hosts this component
- [[concepts/magnitude-calibration]] — The magnitude capture ratio concept
- [[concepts/brier-score]] — The Brier score calibration metric
- [[concepts/intraday-hit-metrics]] — Intraday target hit evaluation
