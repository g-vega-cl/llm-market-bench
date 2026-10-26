---
tags: [portfolio, cash-only, initialization, metrics, accounting]
category: concept
---

# Portfolio Metrics Initialization

When a `Portfolio` is created or loaded, its accounting metrics (`total_equity`, `buying_power`, `excess_liquidity`, `maintenance_margin`, `realized`, `sma`) are fully populated rather than left as placeholders. The engine runs a **Cash-Only** account model — there is no margin borrowing, so buying power is exactly the liquid cash balance. This keeps new and legacy rows consistent with rows written by the systematic strategies.

## New Portfolios

Creating a new account seeds $10,000 cash, sets `sma` to that same cash balance, then calls `calculate_reg_t_metrics({})` to derive the full metric set before the insert. A fresh $10k cash account therefore lands with:

- `total_equity` = 10,000
- `buying_power` = 10,000 (equal to cash — no leverage)
- `excess_liquidity` = 10,000
- `maintenance_margin` = 0
- `sma` = 10,000 (tracks available cash)
- `realized` = 10,000

All of these are inserted in the single `portfolios` insert, so the row is never left with NULL metric columns.

## Existing Portfolios With NULL Metrics

Legacy rows that predate metric persistence can carry NULL `total_equity` / `buying_power` / etc. On load, the class detects missing metrics and re-derives them via `calculate_reg_t_metrics({})` so the in-memory object always has a valid metric set. This makes the downstream `save_metrics()` calls from the strategies idempotent and safe regardless of the row's original state.

## Metric Derivation Under Cash-Only

`calculate_reg_t_metrics()` no longer computes Reg T initial/maintenance margin or the SMA ratchet. It returns:

- `total_equity` = cash + mark-to-market stock value
- `maintenance_margin_req` = `0.0`
- `initial_margin_req` = `0.0`
- `available_funds` = `max(0.0, cash_balance)`
- `excess_liquidity` = `max(0.0, cash_balance)`
- `sma` = `max(0.0, cash_balance)`
- `buying_power` = `max(0.0, cash_balance)`

A negative cash balance (legacy overdraft) yields zero buying power rather than a leveraged capacity. See [[concepts/execution]].

## Frontend Fallbacks

The dashboard mirrors this defense-in-depth: portfolio cards and the detail page render `total_equity ?? cash_balance ?? 0` and `buying_power ?? cash_balance ?? 0` so that a portfolio lacking persisted metrics still displays a sensible value instead of `$0.00`. See [[entities/web-app]].

## Related

- [[concepts/execution]] — Cash-Only trade capacity and guardrails
- [[concepts/systematic-strategy-hooks]]
- [[concepts/pending-settlement-state]]
- [[entities/portfolio-auditor]]
- [[entities/reset-state]] — resets portfolios back to the $10k cash-only default
- [[entities/web-app]]
