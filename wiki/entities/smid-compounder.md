---
tags: [engine, portfolio, small-cap, quality-factor, execution]
category: entity
---

# SMID Quality Compounder

System portfolio (`sys-smid-quality-compounder`) implementing a zero-ceiling small/mid-cap quality compounder strategy. Screens US equities ($1B–$10B market cap) for positive GAAP net income, free cash flow, ROIC > 10%, and 12-month momentum, then retains winners indefinitely regardless of market cap expansion.

## Architecture

- **`apps/engine/analytics/smid_quality.py`** — Quality and momentum factor evaluation: trailing 4-quarter GAAP net income, FCF, ROIC, debt-to-equity, 12-month relative strength, and exit condition logic (unprofitable zombie, cash burn, debt distress).
- **`apps/engine/execution/smid_compounder.py`** — Rebalance order computation: liquidates deteriorating holdings, retains quality winners, allocates freed cash to top-ranked new candidates with slippage modeling.
- **`apps/engine/tasks/smid_compounder_task.py`** — Scheduled task (quarterly rebalance + monthly health check) that fetches live data from FMP and Polygon, evaluates holdings, and executes trades via the Portfolio class.
- **`apps/engine/scripts/dry_run_smid_compounder.py`** — End-to-end dry run script for live market screening and simulated portfolio allocation.
- **`apps/engine/tests/test_smid_quality.py`**, **`apps/engine/tests/test_smid_portfolio.py`**, **`apps/engine/tests/test_smid_task.py`** — Unit tests with zero network calls.

## Strategy Rules

1. **Entry Screen**: Market cap $1B–$10B, 4 quarters positive GAAP net income, positive TTM FCF, ROIC > 10%, debt/equity ≤ 3.0, top quintile 12-month momentum.
2. **Zero-Ceiling Invariant**: Never sell a holding because it grew into a large cap. Multi-baggers ride indefinitely.
3. **Strict Exit**: Sell only if TTM net income turns negative, 2 consecutive quarters of negative FCF, or debt/equity exceeds 3.0.
4. **Cadence**: Quarterly rebalance (Feb, May, Aug, Nov) + monthly health check.

## Related

- [[concepts/small-cap-quality-premium]] — Academic foundations (Asness et al. 2018, Petajisto 2011, Chen et al. 2006)
- [[entities/engine]] — Python data engine
- [[entities/pipeline]] — Daily pipeline
- [[concepts/system-portfolios]] — Mechanical portfolio execution
