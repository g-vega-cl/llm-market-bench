---
tags: [calibration, evaluation, confidence, conviction, scoring]
category: concept
---

# Conviction Points (CP)

Conviction points score a model's self-reported confidence against the outcome. They replace the Brier-derived accuracy penalty everywhere a prediction is scored: daily SPY/TLT, earnings, sector, and the LLM leaderboard.

The design goal is narrow and testable: a confident-and-correct call should earn generously, a confident-and-wrong call should cost heavily, and hedging should never pay. The metric is the logarithmic scoring rule recentred so a coin flip is worth exactly zero.

## Formula

For a directional call with stated probability $p$ (confidence / 100):

$$
CP(p, \text{correct}) = 100 \cdot \ln(2p)
$$

$$
CP(p, \text{wrong}) = 100 \cdot \ln(2 - 2p)
$$

with $p$ clamped to $[0.50, 0.99]$ and $CP = 0$ for $p \le 0.50$.

| Stated confidence | Correct | Wrong |
|---|---|---|
| 55% | +9.53 | −10.54 |
| 60% | +18.23 | −22.31 |
| 75% | +40.55 | −69.31 |
| 95% | +64.19 | −230.26 |

The penalty always exceeds the reward at equal confidence, and the ratio grows with conviction (1.1× at 55%, 3.6× at 95%). The 99% ceiling is the only bound on the penalty; a 100% call is scored as 99%.

## Why This Shape

A naive "reward generously when right, punish heavily when wrong, scaled by confidence" scheme is degenerate. Its expected value is

$$
E = c(p)\,(2q - 1)
$$

where $q$ is the true hit rate. The confidence weight $c(p)$ survives the expectation, so the maximal strategy is always to claim 100%. Any monotone confidence multiplier collapses to bravado.

The log score avoids this because it is **strictly proper**: the expected score is maximised by reporting the true probability. A model that is right 60% of the time maximises its score by stating 60%. Stating 95% lowers it. Stating 55% also lowers it, but only mildly — coyness is punished less than recklessness, which is the correct ordering.

## Aggregation

Mean CP across evaluated predictions feeds three derived values:

- `conviction_norm` = $50 + 50\tanh(\overline{CP}/50)$ — the 0–100 composite term, centred at 50.
- `rank_score` = $\overline{CP} \cdot n/(n+10)$ — sample-size shrinkage so three lucky calls cannot outrank a season.
- `tail_gap` = claimed minus realised hit rate inside the $\ge 90\%$ bucket. Positive means overconfident.

An empty or unscored record set resolves to neutral 50, never zero.

## Ratchet Baseline Guard

The weekly ratchet compares the active prompt's live score against the highest stored variant score, so a single lucky week can pin the baseline above anything the model can reproduce and force a revert every cycle. Two guards prevent that:

- `MIN_BASELINE_SAMPLE = 5` — a variant must carry at least five evaluated predictions before it may set the baseline.
- `shrunk_baseline_score(score, n)` — the candidate ceiling is shrunk toward a neutral 50 prior by $n/(n+10)$. Five calls keep only a third of their apparent edge; twenty keep two thirds.

Both live in `core/conviction_scoring.py` and are applied by `select_baseline_candidate()`, which both autoresearch loops call. The historical realignment utility (`apps/engine/tasks/realign_predictor_baseline.py`) uses the same selector per model track, and the one-shot backfill (`apps/engine/scripts/backfill_conviction_scores.py`) shares its recomputation logic through `core/conviction_backfill.py`.

## Where It Applies

| Surface | Persisted field | Composite weight |
|---|---|---|
| `daily_predictions` | `conviction_score` | 10% of the daily ratchet score |
| `earnings_predictions` | `conviction_score` | diagnostic / leaderboard |
| `sector_predictions` | `conviction_score` | 10% of the sector ratchet score |
| `get_llm_leaderboard_metrics` | `conviction_score` column | 30% of reasoning quality |

The daily and sector ratchet scores keep their existing accuracy pillars but scale them to 0.90:

$$
\text{Score} = 0.90 \cdot \text{accuracy\_block} + 0.10 \cdot \text{conviction\_norm}
$$

Sector legs are priced separately: the best pick uses `confidence`, the worst pick uses the new `worst_confidence` column. Legacy rows without `worst_confidence` skip the worst leg entirely rather than borrowing the best-pick probability.

## Relationship to Brier

Brier remains stored on every prediction row as a calibration diagnostic and is still imported directly by `apps/engine/local_autoresearch/single_prompt_ratchet.py`. It is no longer a scoring input anywhere else. See [[concepts/brier-score]].

## Frontend Presentation

The engine persists the raw per-prediction log-score in `conviction_score`; the web layer never recomputes it from confidence. `apps/web/src/shared/conviction.ts` exposes `normalizeConvictionPoints(meanCp)` (`50 + 50·tanh(cp/50)`), `meanConvictionPoints(predictions)` (averages only rows with a finite stored value, `null` when none), and `resolveConvictionScore(predictions)` (neutral 50 for unscored sets). Every surface that shows a conviction figure — `DailyScoreBreakdown`, `DailyMetricsOverview`, `PredictionsTable`, `DailyPredictionsBacktestPage`, `SectorScoreBreakdown`, and `EarningsArenaTab` — routes through these helpers, and `ModelComparison` treats conviction as a ranked metric while average stated confidence stays informational.

## Consequences

Scores drop broadly when this ships. A model that was paid for stated confidence regardless of accuracy — or that was only lightly docked by a `mean_brier × 50` term — loses that subsidy. That is the metric working, not a regression.

Stored scores must be rewritten once, because the ratchet compares against them. `apps/engine/scripts/backfill_conviction_scores.py` recomputes `conviction_score` on every evaluated row and rewrites the daily and sector `prompt_experiments.metrics` under the new formula. It was run against the archive database on 2026-11-05; rerun it with `--apply` after any future scoring change that invalidates stored history.

## Source

- `apps/engine/core/conviction_scoring.py` — scoring primitive and bundle
- `apps/engine/core/test_conviction_scoring.py` — properness sweep and anti-degeneracy test
- `apps/engine/scripts/backfill_conviction_scores.py` — one-shot row and experiment-metric rewrite
- `apps/web/src/shared/conviction.ts` — presentation aggregation helpers
- `supabase/migrations/20261105000000_add_conviction_scoring.sql` — columns and leaderboard RPC

## Related

- [[concepts/brier-score]]
- [[concepts/auto-research-prompt-improver]]
- [[concepts/intraday-hit-metrics]]
- [[concepts/magnitude-calibration]]
- [[entities/sector-predictor-arena]]
- [[entities/daily-score-breakdown]]
- [[entities/llm-leaderboard]]
