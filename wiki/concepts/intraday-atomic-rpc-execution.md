---
tags: [intraday, execution, rpc, atomic, idempotency, postgres, live-spy-trader]
category: concept
---

# Intraday Atomic RPC Execution

The live intraday homepage trader (`apps/engine/trading/intraday_portfolio.py`, `execute_intraday_portfolio_turn`) executes BUY and SELL fills through the **`execute_portfolio_trade`** Postgres RPC instead of separate `trades` inserts and `portfolio_positions` upserts/deletes. The RPC commits the trade, position, and portfolio metrics atomically under row locks, so the ledger can never end up half-written.

## What Changed

Previously the turn handler did the accounting in Python: it computed cost/proceeds, inserted a `trades` row, upserted or deleted the `portfolio_positions` row, and mutated local `cash_balance` / `current_shares` / `cost_basis`. Now a single `sb_client.rpc("execute_portfolio_trade", {...})` call performs all of it and returns the authoritative post-trade state.

## RPC Parameters

`execute_intraday_portfolio_turn` passes:

| Param | Value |
| :--- | :--- |
| `p_portfolio_id` | the portfolio UUID |
| `p_ticker` | the ticker |
| `p_signal` | `BUY` or `SELL` |
| `p_quantity` | requested shares |
| `p_price` | execution price |
| `p_reason` | the short human-facing `thought` |
| `p_reasoning_trace` | the full reasoning trace |
| `p_idempotency_key` | deterministic UUIDv5 (see below) |
| `p_mark_prices` | `{ticker: current_price}` for mark-to-market |

## Idempotency Key

The key is a `uuid.uuid5(uuid.NAMESPACE_URL, ...)` over `intraday:{portfolio_id}:{ticker}:{signal}:{shares}:{YYYYMMDDTHHMM}` (UTC, minute granularity). A retried HTTP/RPC request with the same key replays the original trade instead of double-executing: the RPC returns the existing `trade_id`, `cash_balance`, `quantity`, `total_cost`, `realized_pnl`, `realized_pnl_pct`, and current position, with `idempotent_replay: true`. A key reused by a different portfolio/ticker raises.

## Return Payload & Local State Sync

The handler reads the JSONB result and refreshes its local variables from the authoritative values: `trade_id`, `cash_balance`, `position_quantity`, `position_avg_cost`, and `realized_pnl`. On a SELL with no position fields returned it falls back to zeroing shares and cost basis. The Alpaca mirror (`_mirror_to_alpaca`) runs **after** the RPC commits, using the returned `trade_id` and the same `trade_signal`, so the ledger is already durable when the mirror is attempted.

## RPC Semantics (migration `20261126150000_execute_portfolio_trade_reasoning_trace.sql`)

`execute_portfolio_trade` is `SECURITY DEFINER`, `search_path = public`, granted to `service_role` only. It:

- Validates non-empty ticker, `signal IN ('BUY','SELL')`, positive integer quantity, and finite positive price.
- Locks the `portfolios` row `FOR UPDATE` to serialize concurrent trades for the same portfolio.
- Replays on `idempotency_key` match (guarding against cross-portfolio reuse).
- Locks the matching `portfolio_positions` row `FOR UPDATE`.
- **BUY**: rejects when `price * qty > cash_balance`; updates or inserts the position with a recomputed weighted average cost basis.
- **SELL**: rejects when no position is held; caps quantity to the held amount; computes `realized_pnl` and `realized_pnl_pct`; deletes the position when fully closed.
- Inserts the `trades` row (including `reasoning_trace`, `idempotency_key`, `alpaca_status`).
- Derives cash-only Reg-T metrics and `total_equity` from locked post-trade state (`buying_power = sma`, `excess_liquidity = sma`, `maintenance_margin = 0`, `realized = cash + positions_cost`).
- Returns the JSONB payload described above.

The migration adds the `p_reasoning_trace TEXT DEFAULT NULL` parameter (dropping the prior 10- and 11-arg signatures first) so the intraday live-spy-trader path has parity with the reasoning trace stored on `trades`.

## Related

- [[entities/intraday-portfolio]] — the live intraday homepage trader
- [[concepts/atomic-trade-execution]] — the atomic settlement pattern
- [[concepts/execution]] — trading execution layer
- [[concepts/alpaca-order-sync]] — the broker mirror that runs after the RPC commits
- [[entities/database]] — `execute_portfolio_trade` RPC and migrations
