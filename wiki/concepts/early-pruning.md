---
tags: [autoresearch, double-ratchet, pruning, optimization, curriculum]
category: concept
---

# Early Pruning

Early pruning is a compute-saving mechanism in the double-ratchet curriculum tournament that aborts evaluation of a candidate prompt after a minimum number of weeks once it is provably unviable. Instead of running a candidate through the full multi-week walk-forward curriculum, the tournament stops early when the candidate's partial results make it mathematically impossible (or statistically hopeless) to beat the current champion.

## Why It Matters

Each curriculum batch runs a candidate across many weeks of daily sessions, and every session is an expensive LLM evaluation. A candidate that is losing badly after the first couple of weeks will almost never recover enough to beat the champion, so continuing to evaluate it wastes time and API budget. Early pruning cuts that waste while preserving the integrity of the tournament — a pruned candidate is simply never accepted.

## Pruning Triggers

After each completed week (once `early_prune_min_weeks` weeks have elapsed and before the final week), the tournament computes the candidate's traded win rate, directional skew, and checks three independent conditions:

1. **Low win-rate floor** — the candidate's traded win rate so far is at or below `early_prune_win_rate_threshold` (default `0.25`, i.e. 25%).
2. **Mathematical impossibility** — the maximum possible final win rate, computed as `(current_correct + remaining_sessions) / total_sessions`, is still below the champion's win rate. Even if every remaining session were a win, the candidate could not overtake the champion.
3. **Directional Collapse / Bias Degeneracy** — the candidate collapses into unidirectional bias (where $\ge 80\%$ of all predictions share the same direction, `early_prune_max_direction_skew=0.80`) AND delivers a coin-flip or worse win rate (`early_prune_directional_skew_max_wr=0.52`). This cuts off runs where the model defaults to blind permabull or permabear guessing across contrasting market regimes.

If any condition fires, the remaining weeks are skipped, `metrics["early_pruned"]` is set to `True`, `metrics["prune_reason"]` records the specific trigger, and the candidate is discarded regardless of its raw score.

## Parameters

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `early_prune` | `True` | Master switch for the mechanism |
| `early_prune_min_weeks` | `2` | Weeks that must complete before pruning is considered |
| `early_prune_win_rate_threshold` | `0.25` | Traded win-rate floor that triggers pruning |
| `champion_win_rate` | current champion's `traded_win_rate_pct` | Used for the impossibility check |
| `early_prune_directional_bias` | `True` | Toggle for directional skew degeneracy abort |
| `early_prune_max_direction_skew` | `0.80` | Skew threshold (e.g. 80%+ UP or DOWN) |
| `early_prune_directional_skew_max_wr` | `0.52` | Maximum win rate allowed before skew triggers abort |

## Acceptance Interaction

A pruned candidate is never accepted: `is_accepted = (not is_early_pruned) and (cand_score > champion_score)`. The tournament log tags such candidates with `[EARLY PRUNED (<reason>)]` so the reason for rejection is visible in the run output.

## CLI

The runner exposes `--early-prune` / `--no-early-prune` (default enabled) and `--early-prune-directional-bias` / `--no-early-prune-directional-bias` (default enabled), printing active settings at startup.

## Related

- [[concepts/strata-laya-double-ratchet]] — the tournament this mechanism belongs to
- [[entities/local-autoresearch]] — the package that hosts the curriculum evaluation
- [[concepts/multi-track-autoresearch]] — related autoresearch orchestration
