---
tags: [concept, autoresearch, overfitting-prevention, cross-validation, jev]
category: concept
---

# Locked Vault & Non-Chronological Weekly K-Fold

The Local Autoresearch loop needs to score candidate decision criteria and data manifests without fooling itself into overfitting the most recent market regime. It does so with two cooperating mechanisms implemented in `apps/engine/local_autoresearch/jev_evaluator.py`: an **atomic weekly grouped K-fold** and a **hidden Locked Vault**.

## Atomic Weekly Blocks

Historical days are grouped into atomic **ISO calendar weeks** (`YYYY-Www`) by `get_iso_week_key()` in `cache_builder.py`. Weeks are the smallest unit that may be assigned to a train or test split — days inside a Monday–Friday week are never separated. This respects the strong intra-week autocorrelation of equity markets and prevents leakage between adjacent sessions.

## Non-Chronological Shuffle

`evaluate_weekly_kfold()` shuffles the week keys with a seeded RNG (`random.Random(seed)`) before splitting them. Because the split is not chronological, the optimizer cannot implicitly favor a training set that happens to be adjacent in time to the test set. A deterministic `train_ratio` (default `0.75`) of weeks becomes TRAIN and the remainder becomes TEST.

## Overfit Penalty

A prompt that scores well in-sample but collapses out-of-sample is penalized rather than rewarded:

$$\text{Overfit Penalty} = \max(0, \text{Score}_{\text{train}} - \text{Score}_{\text{test}})$$

$$\text{Effective Score} = \text{Score}_{\text{test}} - 0.5 \times \text{Overfit Penalty}$$

The **canonical ratchet** therefore optimizes for generalization, not memorization. Per-week metrics (split label, day count, close accuracy, traded win rate, ratchet score) are returned as `weekly_breakdown` for the terminal scoreboard and the Markdown artifact.

## The Locked Vault

`split_weekly_vault()` deterministically partitions all historical weeks into an **Active Optimization Pool** and a **Locked Vault** (default `vault_ratio = 0.20`, seeded). The vault weeks are never shown to the meta-researcher, so candidate mutations are never tuned against them.

If a candidate beats the active baseline on the pool, the runner evaluates it on the vault before accepting it. Acceptance requires:

$$\text{Vault Score} \ge \max(40.0, \text{Baseline Vault Score} - 10.0)$$

A candidate that beats the pool but drops below this threshold is rejected with the `vault_overfit` status (`🛡️ VAULT OVERFIT`) — an explicit overfitting tripwire. Successful candidates update the running baseline vault score so later generations must keep generalizing. Weeks are only partitioned when at least four week blocks exist; otherwise the whole dataset forms the active pool.

## Related

- [[entities/local-autoresearch]] — the loop that runs this cross-validation
- [[concepts/curated-data-manifest]] — the feature-selection lever scored by this scheme
- [[concepts/confidence-gating]] — the other lever the meta-researcher evolves
- [[concepts/multi-track-autoresearch]] — the remote weekly ratchet counterpart
