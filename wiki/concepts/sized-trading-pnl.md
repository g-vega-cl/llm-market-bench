---
tags: [autoresearch, quant, pnl, sharpe, kelly, walk-forward, feature-conditioning]
category: concept
---

# Sized Trading PnL & Quant Analytics

The quantitative analytics layer in `apps/engine/local_autoresearch/quant_analytics.py` converts directional prediction records into risk-adjusted trading metrics, standardized feature vectors, walk-forward folds, and two-sided promotion gates. It is the scoring and conditioning backbone of the [[concepts/single-prompt-ratchet]] tournament.

## Position-Sized PnL

`calculate_sized_trading_pnl(records)` treats each prediction as a confidence-scaled directional bet on the SPY Open-to-Close return:

- **Direction sign**: `+1` for UP, `-1` for DOWN.
- **Position size**: `(confidence - 50) / 50`, clamped to `[0, 1]`. A 50% confidence call takes no position; 100% takes full size.
- **Sized return**: `sign × raw_return × size`.

It returns cumulative and unweighted returns, mean daily return, daily return standard deviation, annualized Sharpe (252 trading days), win/loss payoff ratio, profit factor, and maximum drawdown of the compounded sized equity curve. Empty or invalid records return a zeroed metric block.

This objective rewards high-confidence calls that coincide with large realized moves and penalizes high-confidence misses on counter-trend days, unlike raw binary accuracy.

## Standardized Quantitative Feature Vector

`format_normalized_quant_vector(session)` emits a compact tabular block before narrative context:

- SPY overnight gap, QQQ-vs-SPY gap spread, and TLT gap (bond-yield proxy).
- Options put/call volume and open-interest ratios, max-pain strike with distance from open, and ATM implied volatility.

Missing fields degrade gracefully to `Not Provided / N/A`. The block anchors model reasoning in numerical differentials before it reads newsletter prose.

## Walk-Forward Splits

`create_walk_forward_splits(sessions, n_splits=3, min_train_size=10)` builds expanding-window folds over chronologically sorted sessions. Each fold's training window ends before its test window begins. If there are too few sessions, it returns a single full-data fold with an empty test set.

## Two-Sided Promotion Gate

`passes_two_sided_gate_discrete(metrics, min_recall_up=54.0, min_recall_down=54.0, min_bal_acc=58.0, min_mcc=0.20)` rejects candidates that are bear-biased or bull-biased:

- Recall UP below threshold → `Bear-biased`.
- Recall DOWN below threshold → `Bull-biased`.
- Balanced accuracy or MCC below threshold → rejected.

The discrete boundary is intentional: 6/11 UP recalls (54.55%) passes a 54.0% floor, while 5/11 (45.45%) fails. This prevents a perma-bear prompt from winning on a DOWN-heavy sample.

## Related

- [[concepts/single-prompt-ratchet]] — tournament loop that consumes these metrics
- [[concepts/ground-truth-autoresearch-leakage-guards]] — balanced accuracy and holdout gating rationale
- [[concepts/quant-ml-sp500-directional-blueprint]] — return-weighted Sharpe and Kelly sizing theory
- [[entities/local-autoresearch]] — local runner and Strata integration
