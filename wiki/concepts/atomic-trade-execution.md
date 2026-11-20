---
tags: [execution, atomicity, idempotency, postgres, rpc, retries, sandbox, concurrency]
category: concept
---

# Atomic Trade Execution

Every portfolio mutation on the platform goes through a single PostgreSQL function, `public.execute_portfolio_trade`, instead of a sequence of independent PostgREST round-trips. The RPC locks the portfolio row, validates the request, mutates `portfolio_positions`, inserts the `trades` ledger row, and recomputes `portfolios` metrics **inside one transaction**, returning the committed state as JSON. This eliminates the partial-write class of bug where cash was deducted but the trade row (or the position) never landed, silently desyncing a portfolio's `cash_balance` from its real ledger.

See [[concepts/execution]] for the surrounding execution phase and [[entities/database]] for the table inventory.

## Why the Multi-Write Path Was Unsafe

The previous implementation performed three independent writes from Python:

1. `portfolio_positions` upsert/delete,
2. `trades` insert,
3. `portfolios` update (cash / SMA),

followed later by an unlocked `save_metrics()`. A failure between (2) and (3) left the position mutated with cash untouched; a retried HTTP request on a 502/504 could insert the trade twice. Both outcomes are CP-violating for a financial ledger (see [[concepts/staff-engineer-verification]] on fail-closed state).

## The RPC Contract

`supabase/migrations/20261119050000_atomic_execute_portfolio_trade_rpc.sql`:

```sql
public.execute_portfolio_trade(
    p_portfolio_id UUID,
    p_ticker TEXT,
    p_signal TEXT,
    p_quantity INTEGER,
    p_price NUMERIC,
    p_decision_id UUID DEFAULT NULL,
    p_reason TEXT DEFAULT NULL,
    p_idempotency_key UUID DEFAULT NULL,
    p_mark_prices JSONB DEFAULT NULL
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
```

`EXECUTE` is revoked from `PUBLIC` and granted only to `service_role`, matching the [[concepts/supabase-grant-convention]] posture for privileged mutation RPCs.

### Validation (fail fast, before any write)

- ticker must be non-empty after `UPPER(BTRIM(...))`;
- signal must be exactly `BUY` or `SELL`;
- quantity must be positive;
- price must be finite, positive, and `<= 1e9` (a `NaN` or absurd price aborts the whole call).

Each failure raises a PL/pgSQL `RAISE EXCEPTION` (SQLSTATE `P0001`), which rolls the transaction back and is treated as non-retryable by the client (see below).

### Row locking

The function opens with `SELECT cash_balance, sma, total_equity FROM portfolios WHERE id = p_portfolio_id FOR UPDATE`, serializing concurrent trades against the same portfolio. The position row is then locked with a second `FOR UPDATE` on `(portfolio_id, ticker)`.

### Buy / sell semantics

- **BUY** — rejects when `price * quantity > cash_balance`; otherwise debits cash, and either averages the cost basis into the existing position (`(avg_cost * old_qty + total_cost) / new_qty`) or inserts a new `portfolio_positions` row.
- **SELL** — rejects when no position is held; otherwise caps `v_exec_qty = LEAST(p_quantity, v_pos_qty)`, credits cash, and writes `realized_pnl = (price − avg_cost) * exec_qty` with `realized_pnl_pct = (price / avg_cost − 1) * 100` (0 when the cost basis is zero). A full exit deletes the position row; a partial exit leaves the average cost basis untouched.

### Metrics derived in SQL, not in Python

After the position mutation the function recomputes, from the locked post-trade position set:

- `positions_cost = Σ quantity × average_cost_basis`;
- `positions_mv = Σ quantity × mark`, where `mark` is `p_mark_prices ->> UPPER(ticker)` when it is present, finite, and positive, else the trade price for the traded ticker, else the average cost basis;
- `realized = new_cash + positions_cost`;
- `total_equity = new_cash + positions_mv`;
- `sma = buying_power = excess_liquidity = GREATEST(0, new_cash)`, `maintenance_margin = 0`.

This keeps the Cash-Only account model ([[concepts/portfolio-metrics-initialization]]) authoritative inside the transaction. Callers no longer run a separate `save_metrics()` after a trade, so an unlocked post-write metric overwrite cannot resurrect stale numbers.

### Idempotent replay

`trades.idempotency_key UUID` is added with a **partial unique index** (`WHERE idempotency_key IS NOT NULL`), plus `(portfolio_id, executed_at DESC)` and `(portfolio_id, signal, executed_at DESC)` indexes for the ledger reads used by the sentiment fader and auditors.

When `p_idempotency_key` is supplied and already present:

- a mismatched `portfolio_id`/`ticker` for the same key raises (`Idempotency key … already used by another trade`) — a key is never silently reused across trades;
- a matching replay returns the original `trade_id`, committed cash/SMA/equity, and the current position snapshot with `idempotent_replay: true`, writing nothing.

This is what makes a retry after a timeout safe: if the first attempt committed and the response was lost, the second attempt replays instead of double-charging. The scenario is pinned by `test_execute_trade_idempotent_replay_after_commit_timeout`.

## Python Client Side (`apps/engine/execution/portfolio.py`)

`Portfolio.execute_trade` is now a thin coordinator:

1. **`_validate_trade_preflight(ticker, quantity, price, signal)`** — validates quantity/price/signal and local cash/held-quantity bounds **without mutating in-memory state**, returning `(quantity, ok)`. Invalid signals, non-finite prices, and sells of unheld tickers are rejected before the database is touched.
2. **Mark prices** — builds `merged_prices` from the caller's `current_prices` (falling back to average cost basis per position) and stamps the traded ticker at the execution price, then sends it as `p_mark_prices` so SQL can compute mark-to-market equity.
3. **Fresh idempotency key** — `str(uuid4())` per call, reused across every retry of that same call.
4. **`async_with_retry(...)`** — executes the RPC in a worker thread and retries transient failures with exponential backoff, keeping the same idempotency key on every attempt.
5. **`_sync_local_state_from_rpc(ticker, payload, merged_prices)`** — adopts the committed `cash_balance`, `sma`, `position_quantity`, and `position_avg_cost` into the in-memory `Portfolio`, then recomputes Reg-T metrics locally from the returned truth.
6. **Alpaca mirror** — only after the database commit, and only when `skip_alpaca_mirror=False`; a mirror failure can never corrupt the ledger. `exec_qty` (the RPC's capped quantity) is mirrored, not the requested quantity.

Any exception from the RPC logs via `logger.exception` and returns `None` with **zero** local or remote mutation.

## Transient Error Classification (`core/db.py`)

`is_transient_supabase_error` decides whether a failed call is worth retrying:

- **`status_code` attribute** — `429`, `502`, `503`, `504` are transient (PostgREST/supabase-py often expose the status directly).
- **Structured SQLSTATE `P0001`** — an explicit `RAISE EXCEPTION` from business logic (
