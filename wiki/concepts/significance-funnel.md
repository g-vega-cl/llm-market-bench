---
tags: [autoresearch, double-ratchet, statistics, hypothesis-testing, curriculum]
category: concept
---

# Significance Funnel

The Significance Funnel is an adaptive, multi-stage evaluation mechanism in the double-ratchet local autoresearch loop. It addresses small-sample variance by progressively escalating promising candidate prompts through expanded multi-regime testing and verifying that outperformance is statistically significant (p < 0.05) against a random 50% coin-flip null hypothesis before any prompt pair can be accepted as champion.

## Why It Matters

In standard 5-week curriculum batches (N ≈ 20–25 trading sessions), a candidate achieving 14 wins out of 23 sessions (60.9% win rate) yields a one-tailed binomial p-value of p = 0.2024. A random 50/50 coin flip produces this result roughly 1 out of 5 times by pure chance. Without multi-stage expansion, an early lucky batch can establish an artificially inflated champion score that discards truly robust, long-term 56%–58% alpha candidates.

Conversely, running every mutation across 100+ sessions would require 5–7 hours per candidate on local hardware. The Significance Funnel solves this trade-off by acting as an adaptive filter: unviable runs are discarded early, while candidates exceeding a promising threshold are automatically escalated to multi-regime evaluation.

## Architecture

The funnel operates across two progressive stages:

1. **Stage 1: Screening Sieve (N = 20–25 sessions)**
   - Fast walk-forward run over a single 5-week curriculum batch.
   - Candidates are subjected to [[concepts/early-pruning]] (low win-rate floor ≤ 25% or directional collapse ≥ 80% one-way bias with ≤ 52% win rate).
   - If the candidate finishes with `traded_win_rate` ≥ `promising_win_rate` (default 58.0%) and beats the champion score, it is flagged as promising and escalated.
   - Candidates below 58.0% are discarded immediately, saving compute.

2. **Stage 2: Multi-Regime Expansion (N = 65–75 cumulative sessions)**
   - Automatically samples `stage2_expansion_weeks` (default 10 weeks) across distinct, contrasting market regimes (e.g. low-vol grind, CPI shock drawdowns, high-ATR whipsaws) not present in Stage 1.
   - Evaluates the candidate across these expanded weeks and aggregates cumulative trading sessions.
   - Executes an exact one-tailed binomial test:
     H0: p = 0.50  vs  H1: p > 0.50
   - To pass Stage 2, the candidate must maintain cumulative `win_rate` ≥ `promising_win_rate` and achieve statistical significance:
     p-value ≤ α  (α = 0.05)
   - Candidates that fade in contrasting regimes are tagged with a prune reason and rejected.

## Parameters

| Parameter | Default | Meaning |
| :--- | :---: | :--- |
| `escalate_promising` | `True` | Master toggle for Stage 2 multi-regime expansion |
| `promising_win_rate` | `0.58` (58%) | Win-rate threshold required in Stage 1 to trigger escalation |
| `significance_alpha` | `0.05` | Maximum p-value threshold for binomial hypothesis rejection |
| `stage2_expansion_weeks` | `10` | Number of contrasting curriculum weeks added in Stage 2 |
| `early_prune_stage2` | `True` | Enforces early pruning during Stage 2 expansion passes |

## Implementation

The logic is isolated as a vertical slice in `apps/engine/local_autoresearch/significance_funnel.py` with colocated tests in `apps/engine/local_autoresearch/test_significance_funnel.py`. It is invoked by `run_double_ratchet_curriculum_tournament` in `apps/engine/local_autoresearch/double_ratchet.py` and exposed via CLI flags (`--escalate-promising`, `--promising-win-rate`, `--significance-alpha`, `--stage2-expansion-weeks`) in `apps/engine/local_autoresearch/runner.py`.

Key functions:

- `calculate_binomial_significance` — exact one-tailed binomial test (via `scipy.stats.binomtest`) plus a normal-approximation Z-score.
- `should_escalate_to_stage2` — gates escalation on non-pruned candidates with `traded_win_rate_pct` ≥ threshold.
- `sample_contrasting_regime_weeks` — deterministically samples unseen weeks (seeded) for Stage 2.
- `evaluate_stage2_escalation` — runs the expansion batch, combines Stage 1 + Stage 2 results, and applies the significance test.

## Related

- [[concepts/strata-laya-double-ratchet]] — double-ratchet tournament loop hosting the funnel
- [[concepts/early-pruning]] — compute-saving candidate abort mechanism
- [[entities/local-autoresearch]] — package managing local prompt optimization
