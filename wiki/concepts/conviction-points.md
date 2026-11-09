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

**HOLD and unscored calls.** `conviction_points(confidence, correct)` accepts `correct: bool | None`. When `correct is None` (a `HOLD` prediction, or any row with no directional outcome) it returns `0.0` — a neutral coin-flip score. `_evaluated_records` includes `HOLD` rows (with a `None` outcome) so they contribute neutral `0.0` CP to `conviction_norm` rather than being dropped; HOLD rows are also excluded from tail-gap and `confident_wrong_count` accounting.

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

The weekly ratchet compares the active prompt's live score against the highest stored variant score, so a single lucky week can pin the baseline above anything the model can reproduce and force a revert every cycle. Guards prevent that:

- `MIN_BASELINE_SAMPLE = 5` — a variant must carry at least five evaluated predictions before it may set the baseline.
- `MIN_TRADED_SAMPLE = 3` — a variant must also carry at least three *traded* (UP/DOWN) predictions, read from `metrics.traded_count`, so a prompt that largely `HOLD`s cannot pin the baseline on a couple of directional calls.
- `shrunk_baseline_score(score, n)` — the candidate ceiling is shrunk toward a neutral 50 prior by $n/(n+10)$. Five calls keep only a third of their apparent edge; twenty keep two thirds.

All live in `core/conviction_scoring.py` and are applied by `select_baseline_candidate()`, which both autoresearch loops call. The historical realignment utility (`apps/engine/tasks/realign_predictor_baseline.py`) uses the same selector per model track, and the one-shot backfill (`apps/engine/scripts/backfill_conviction_scores.py`) shares its recomputation logic through `core/conviction_backfill.py` (which now writes `0.0` for `HOLD` rows).

## Where It Applies

| Surface | Persisted field | Composite weight |
|---|---|---|
| `daily_predictions` | `conviction_score` | 10% of the daily ratchet score (before participation scaling) |
| `earnings_predictions` | `conviction_score` | diagnostic / leaderboard |
| `sector_predictions` | `conviction_score` | 10% of the sector ratchet score |
| `get_llm_leaderboard_metrics` | `conviction_score` column | 30% of reasoning quality |

The daily and sector ratchet scores keep their existing accuracy pillars but scale them to 0.90:

$$
\text{Score} = 0.90 \cdot \text{accuracy\_block} + 0.10 \cdot \text{conviction\_norm}
$$

The daily predictor additionally multiplies the result by its 75% participation factor, and prices `HOLD` sessions with move-aware credits (see [[concepts/confidence-gating]]). The leaderboard RPC writes `0.0` CP for `HOLD` rows and treats 
