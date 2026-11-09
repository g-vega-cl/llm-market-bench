---
tags: [execution, trading, idempotency, settlement, portfolios]
category: concept
---

# Execution Phase

The execution phase converts validated trade decisions into settled portfolio mutations. It runs after consensus and before feedback in the daily pipeline (see [[entities/pipeline]]).

## Idempotency Cleanup

Daily SPY and TLT close-trade executors (`apps/engine/execution/daily_trading.py`, `apps/engine/execution/daily_bond_trading.py`) are safe to re-run mid-flight. Before evaluating the new prediction, each executor:

1. Queries all `trades` rows for the portfolio within the target session (`executed_at` between `T00:00:00Z` and `T23:59:59Z`).
2. Sums `realized_pnl` **only from exit trades** (`signal` in `SELL` / `COVER`) to avoid double-counting SHORT re-runs where both entry and exit rows carry `realized_pnl`.
3. Reverts the portfolio's `cash_balance`, `total_equity`, `realized`, `buying_power`, and `excess_liquidity` to the pre-trade cash (`max(0.0, current_cash - prev_pnl)`).
4. Batch-deletes the prior session trades via `.in_("id", trade_ids)`.
5. Updates the `portfolios` row with the reverted balances and `last_updated_at`.

The cleanup runs **before** the HOLD gate, so a re-run whose prediction is gated to HOLD still removes stale same-day trades and reverts cash. When the recomputed execution yields `shares <= 0` (insufficient capital), the executor upserts a `portfolio_performance` row reflecting the reverted cash so the daily equity curve stays consistent.

## Related

- [[concepts/pending-settlement-state]] — settlement state tracking
- [[concepts/daily-spy-live-trading]] — SPY daily close executor
- [[concepts/daily-tlt-live-trading]] — TLT daily close executor
- [[entities/pipeline]] — daily pipeline phases
