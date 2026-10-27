---
tags: [concept, daily-predictor, jev, risk-management, zero-abstention, deprecated]
category: concept
---

# Confidence Gating & Zero Abstention (Historical Deprecation)

> [!WARNING]
> **DEPRECATED & PROHIBITED**: Confidence gating to `NO_TRADE` has been permanently superseded by the **Zero Abstention Contract (MANDATORY)**. Every single trading session, all daily predictor models (including `jev-four-regime-champion`) MUST commit to a binary directional call (`UP` or `DOWN`).

## Historical Background

In early iterations of local autoresearch (`jev-local-autoresearched`), an experimental `min_confidence` lever (e.g. $55.0\%$ or $61.0\%$) was introduced. If Jev's output confidence fell below that threshold, the task attempted to gate the decision to `NO_TRADE` under the hypothesis that abstaining during low-conviction regimes would preserve capital.

## Why Confidence Gating Failed (The Selectivity Trap)

As detailed in [[concepts/daily-directional-predictability-limits]] and the Locked Vault stress tests:
1. **The Selectivity Trap / Cowardice**: Gating created perverse incentives in evolutionary ratchet loops where models learned to abstain on choppy or ambiguous regimes, artificially inflating reported win rate while refusing to trade when real market decisions were needed.
2. **Database Invariant Conflict**: The canonical database schema for `daily_predictions` strictly enforces binary classification:
   ```sql
   predicted_direction TEXT NOT NULL CHECK (predicted_direction IN ('UP', 'DOWN'))
   ```
   Emitting `NO_TRADE` caused database insert failures during live production runs.
3. **Training Parity Gap**: The reigning tournament champion (`jev-four-regime-champion`, Iteration 43) was trained and evaluated under the **Zero Abstention Rule** in [[concepts/single-prompt-ratchet]] across 34 real pre-market sessions with 100% binary participation. Leftover `NO_TRADE` code in the runner violated training-production parity.

## Current Architecture: Zero Abstention & Forced Direction

Under the **Zero Abstention Contract** (defined in `apps/engine/local_autoresearch/strata_client.py` and [[entities/local-autoresearch]]):
- `min_confidence` is purged (`0.0%`).
- No model is permitted to output `NO_TRADE`.
- On ambiguous or balanced days, the four-regime classifier assigns lower confidence (e.g. $51\%–54\%$), but **strictly commits to either `UP` or `DOWN`**.
- Evaluation in `apps/engine/tasks/evaluate_daily_predictions.py` scores all sessions based on pure directional correctness.

## Related

- [[entities/daily-market-predictor]] — production prediction runner enforcing forced binary direction
- [[entities/local-autoresearch]] — the local optimization loop enforcing Zero Abstention
- [[concepts/single-prompt-ratchet]] — tournament architecture producing the binary champion
- [[concepts/pure-directional-scoring]] — directional scoring without abstention artifacts
