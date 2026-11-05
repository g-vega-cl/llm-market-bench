---
tags: [daily-predictions, score-breakdown, ui-component]
category: entity
---

# Daily Score Breakdown

An interactive React component (`DailyScoreBreakdown`) that renders a detailed, transparent calculation of the Daily Ratchet Score for a given prompt experiment. It displays the weighted formula substitution, four pillar metric tiles, sample window metadata, low-sample sensitivity warnings, and a collapsible scoring methodology guide.

## Purpose

Provides full auditability of the ratchet score computation directly in the Autoresearch & Benchmark History tab of the Daily Predictions page. Users can see exactly how each factor (directional accuracy, intraday hit rate, magnitude capture, conviction) contributes to the final score, with live arithmetic substitution and per-pillar point contributions.

## Key Features

- **Formula Substitution Bar**: Shows the live arithmetic formula with color-coded factors and computed intermediate values.
- **4 Weighted Pillar Metric Tiles**:
  - EOD Directional Accuracy (55%), green tile with correct/total count
  - Intraday Target Hit Rate (35%), teal tile with targets hit/total count
  - Magnitude Capture Ratio (10%), purple tile with breakout capture ratio
  - Conviction (10%), tile showing the normalised calibrated-confidence term with mean CP (50 = coin flip). Brier is shown only as a diagnostic in the guide.
- **Low Sample Window Notice**: Automatically displayed when $N < 5$, explaining the sensitivity of short evaluation windows.
- **Collapsible Scoring Guide**: Explains the methodology behind each of the four factors.
- **Active Variant Placeholder**: When the experiment is `active` with no resolvable metrics, the component renders the **"Live Variant Evaluation In Progress"** card (with a solid `success` `ACTIVE` badge) instead of a score breakdown.

## Metric Resolution

All three resolution paths funnel through a single shared `buildMetrics(...)` helper so the arithmetic is identical regardless of where the inputs came from. It converts percentages into weighted points and blends in conviction:

```
closeAccPoints        = (closeAccuracyPct / 100) * 55.0
intradayHitPoints     = (intradayHitPct / 100) * 35.0
magnitudeCapturePoints= (magnitudeCapturePct / 100) * 10.0
accuracyBlockPoints   = closeAccPoints + intradayHitPoints + magnitudeCapturePoints
convictionContribution= convictionNorm * 0.10
score                 = accuracyBlockPoints * 0.90 + convictionContribution
```

`mean_brier` is still carried through for the diagnostic line in the guide, but it is not subtracted. See [[concepts/conviction-points]].

An optional `overrideScore` argument replaces the computed score with the engine-persisted value while still deriving the pillar points from the raw percentages.

- **`extractEnrichedMetrics(rawMetrics)`** — reads the engine-persisted enriched metrics (`close_accuracy_pct`, `intraday_hit_pct`, `magnitude_capture_pct`, `conviction_norm`, `conviction_mean_cp`, `mean_brier`, `predictions_evaluated`, `correct_count`, `intraday_hit_count`) and passes the stored `score` as the override.
- **`computeMetricsFromSample(sample, rawScore?)`** — derives the same metrics from the supplied `DailyPrediction[]` array (correct count, intraday hits, magnitude capture, mean conviction points from the stored `conviction_score` column, mean Brier), passing `rawScore` as the override when it is numeric.
- **`resolveRatchetMetrics(experiment, predictions)`** — returns enriched metrics when present, otherwise computes from predictions that belong to the experiment, otherwise returns `null`. There is **no** score-only fallback: an experiment whose `metrics` object carries a numeric `score` but no enriched pillar fields resolves to `null` here, and the caller decides how to render that (see [[concepts/experiment-display-score]]).

## Fluent Layout and Overflow Prevention

The component renders inside nested detail panes that share horizontal space with sidebars, so it is built entirely from design-system primitives and CSS layout utilities — zero inline `style` objects for layout, typography, or color (see [[entities/design-system]]):

- The outer surface is a `Card` with `p-5 flex flex-col gap-4 rounded-none min-w-0`.
- The header row is `flex justify-between items-center flex-wrap gap-3` with a `border-b border-boxel-bevel-hi` divider.
- The formula substitution bar and each pillar tile are recessed `voxel-trough rounded-none` slots.
- The pillar grid steps intrinsically with `grid-cols-[repeat(auto-fit,minmax(min(100%,10rem),1fr))] gap-3 items-stretch` rather than viewport breakpoints or fixed pixel widths.
- Formula text uses `break-words overflow-wrap-anywhere` inside an `overflow-x-auto` trough so long equations wrap cleanly without forcing parent card expansion.
- Pillar values use Tier 1 typography (`text-lg font-bold font-mono tabular-nums`) with semantic signal tokens (`text-success`, `text-info`, `text-accent`, `text-danger`).

## Usage

```tsx
<DailyScoreBreakdown experiment={experiment} predictions={predictions} />
```

- `experiment`: A `PromptExperiment` object with optional enriched `metrics`.
- `predictions` (optional): An array of `DailyPrediction` objects used for fallback computation.

## Related

- [[entities/daily-market-predictor]], The parent feature that hosts this component
- [[concepts/magnitude-calibration]], The magnitude capture ratio concept
- [[concepts/conviction-points]], The calibrated-confidence metric that drives the 10% term
- [[concepts/brier-score]], The Brier score calibration diagnostic (no longer a scoring input)
- [[concepts/intraday-hit-metrics]], Intraday target hit evaluation
- [[concepts/experiment-display-score]], How the UI resolves a display score when metrics are empty
- [[entities/design-system]], Boxel primitives and CSS-first layout rules
