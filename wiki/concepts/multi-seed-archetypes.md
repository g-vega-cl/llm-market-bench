---
tags: [autoresearch, exploration, local-optima, prompt-search, archetypes]
category: concept
---

# Multi-Seed Search Archetypes

Sequential mutation from a single champion risks getting trapped in local optima — minor variations around a fixed gap threshold and confidence gate. The [[entities/local-autoresearch]] orchestrator supports launching discrete tournaments from quantitative *archetype seeds* (`--seed-archetype`) that start the evolutionary search in disjoint regions of the prompt/manifest design space.

## Archetypes

| Archetype | Core Hypothesis | Features Included |
| :--- | :--- | :--- |
| `clean-sheet` | Bare format blocks, zero trading rules — let the model build a strategy from first principles. | Basic OHLC + newsletters |
| `mean-reversion` | Extreme overnight gaps (≥ 0.40%) tend to fill after the open unless confirmed by macro yields and volume. | SPY, QQQ, IWM, TLT, options, intraday VWAP |
| `macro-rates` | 10Y/2Y Treasury yield shifts (TLT/IEF) and 8:30 AM prints drive risk-on/off regimes. | QQQ, TLT, IEF, GLD, economic calendar, options |
| `momentum-breadth` | Pre-market Gap & Go confirmed by tech (QQQ) and small-cap (IWM) breadth. | QQQ, IWM, DIA, intraday VWAP/CLV, options |

## Behavior

When `--seed-archetype` is supplied, the runner evaluates the archetype's criteria against the active weeks (and vault, if present), saves it as the `baseline` record with a `seed-<archetype>-<hex>` tag, and seeds the tournament history at iteration 0. Each archetype can be run into its own local SQLite vault (e.g. `.local_autoresearch_meanrev.db`) to cultivate independent lineages.

## Related

- [[entities/local-autoresearch]] — implements the archetype seeds
- [[concepts/regime-vault]] — out-of-distribution check every candidate faces
- [[concepts/baseline-calibration]] — keeps the watermark comparable across datasets
- [[concepts/locked-vault-kfold]] — the K-fold evaluator used during calibration
