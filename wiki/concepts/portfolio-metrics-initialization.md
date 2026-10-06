---
tags: [portfolio, reg-t, initialization, metrics, accounting]
category: concept
---

# Portfolio Metrics Initialization

When a `Portfolio` is created or loaded, its Reg T accounting metrics (`total_equity`, `buying_power`, `excess_liquidity`, `maintenance_margin`, `realized`) are now fully populated rather than left as placeholders. This keeps new and legacy rows consistent with rows written by the systematic strategies.

## New Portfolios

Creating a new account seeds $10,000 cash and $10,000 SMA, then calls `calculate_reg_t_metrics({})` to derive the full metric set before the insert. A fresh $10k cash account therefore lands with:

- `total_equity` = 10,000
- `buying_power` = 40,000 (4× cash under Reg T initial margin)
- `excess_liquidity` = 10,000
- `maintenance_margin` = 0
- `realized` = 10,000

All of these are inserted in the single `portfolios` insert, so the row is never left with NULL metric columns.

## Existing Portfolios With NULL Metrics

Legacy rows that predate metric persistence can carry NULL `total_equity` / `buying_power` / etc. On load, the class detects missing metrics and re-derives them via `calculate_reg_t_metrics({})` so the in-memory object always has a valid metric set. This makes the downstream `save_metrics()` calls from the strategies idempotent and safe regardless of the row's original state.

## Frontend Fallbacks

The dashboard mirrors this defense-in-depth: portfolio cards and the detail page render `total_equity ?? cash_balance ?? 0` and `buying_power ?? cash_balance * 2` so that a portfolio lacking persisted metrics still displays a sensible value instead of `$0.00`. See [[entities/web-app]].

## Related

- [[concepts/systematic-strategy-hooks]]
- [[concepts/pending-settlement-state]]
- [[entities/portfolio-auditor]]
- [[entities/web-app]]
