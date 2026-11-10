---
tags: [concept, mean-reversion, overreaction, options, volatility, risk-management]
category: concept
---

# Overreaction & Mean-Reversion Discipline

A quantitative framework for distinguishing **statistical overreactions** (mean-reversion opportunities) from **justified structural repricings** (falling-knife traps) on sharp price moves. Implemented in `apps/engine/analytics/overreaction.py` and exposed to agents via the `audit_price_overreaction` pull tool.

## The Problem

When a stock drops sharply, the instinct is to buy the dip. But not all sharp drops are overreactions. Some are justified repricings driven by fundamental deterioration, analyst target cuts, or structural changes. Catching a falling knife on a justified repricing is a classic way to lose money. The audit tool forces the agent to check the evidence before committing capital.

## The Three Verdicts

`classify_overreaction(change_pct, z_score, rvol, cone_multiplier, consensus_cut_pct)` classifies a move into one of three verdicts:

### `STATISTICAL_OVERREACTION`

A mean-reversion opportunity. Requires **all** of:

- Return-shock Z-score `|z| >= 2.0σ` against the historical daily return distribution
- RVOL `>= 1.8x` (capitulation volume / institutional turnover)
- Actual move `>= 1.8x` the options-implied daily move cone
- Analyst consensus targets and revisions remain intact (no severe cuts)

### `JUSTIFIED_REPRICING`

A falling-knife warning. Triggered when:

- Price drop `<= -5.0%` or Z-score `<= -1.5σ`, **and**
- Analyst consensus target cut `<= -15.0%`

A `STATISTICAL_OVERREACTION` candidate is also downgraded to `JUSTIFIED_REPRICING` if the consensus target cut is `<= -15.0%`.

### `NORMAL_VOLATILITY`

The move is within normal `1.5σ` bounds and the expected options cone.

## The Tool

`audit_price_overreaction(ticker, lookback_days=20)` in `apps/engine/tools/overreaction.py` wraps `audit_price_overreaction_report` in `apps/engine/analytics/overreaction.py`.

It fetches:

- Live quote (price, change %, volume, avg volume) via `MarketDataManager.get_quote`
- Historical closes for daily return standard deviation via `MarketDataManager.get_history`
- Options-implied daily move cone via `get_options_vol_surface_report`
- Analyst consensus targets via FMP `/stable/price-target-consensus`

The report renders a Markdown block with the verdict badge, spot price, Z-score, RVOL, options cone multiplier, consensus target revision, and a plain-English setup explanation.

## The Prompt Block

`overreaction_mean_reversion` in `apps/engine/autoresearch/prompt_blocks.py` instructs the agent to:

1. Audit moves before catching knives — invoke `audit_price_overreaction` on any sharp drawdown (`>5%` intraday or `>2σ` move).
2. Only execute mean-reversion entries on `STATISTICAL_OVERREACTION` setups where capitulation volume and cone overshoot occur with intact consensus fundamentals.
3. Avoid longing `JUSTIFIED_REPRICING` falling knives.

## Related

- [[entities/tool-registry]] — canonical tool registry
- [[concepts/modular-prompt-blocks]] — modular prompt blocks catalog
- [[entities/engine]] — the engine hosting the analytics module
