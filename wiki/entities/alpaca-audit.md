---
tags: [alpaca, audit, reconciliation, portfolio]
category: entity
---

# Alpaca Audit Reconciler

**Location**: `apps/engine/audit/alpaca_audit.py`
**CLI Command**: `python main.py audit-alpaca [--model <model_name>] [--days <N>] [--json]`

The **Alpaca Audit Reconciler** reconciles an agent's simulated Supabase portfolio performance against Alpaca brokerage execution, fill prices, slippage, and position state. It provides a comprehensive audit trail for verifying that simulated trades match real brokerage fills.

## Reconciliation Pipeline

1. **Performance Verification**: Compares frontend chart metrics (`portfolio_performance` snapshots) against mark-to-market trade calculations and Alpaca fills.
2. **Trade Matching & Slippage**: Matches each trade ID with Alpaca orders using `client_order_id = {agent_id}__{ticker}__{signal}__{trade_id}` format, calculating execution price slippage per trade.
3. **Position Reconciliation**: Compares Supabase holding quantities against reconstructed Alpaca share counts.
4. **Root-Cause Discrepancy Detection**: Surfaces skipped orders (`SKIPPED_NO_POSITION`), rejected orders, or timing lags.

## Mirror Contract

`AlpacaBroker` is fire-and-forget for every lane except that the caller now receives the outcome:

- `submit_market_order(...)` / `submit_limit_order(...)` share `_submit_order` (running blocking Alpaca SDK calls on `asyncio.to_thread`), persist `DISABLED` when `_client` is absent, and return `{"status": str, "order_id": str | None}` where status is `SUBMITTED`, `REJECTED` (HTTP 4xx `APIError`, with reason in `trades.alpaca_note`), `ERROR` (5xx/timeout/unexpected exception, with reason in `trades.alpaca_note`), `SKIPPED_NO_POSITION`, or `DISABLED` (no client / missing keys). Callers that ignore the return value are unaffected.
- `trades.alpaca_note` carries divergence or failure detail that must not overload the status: the live trader stamps `BROKER_POSITION_MISMATCH (ledger N, broker M)` when it mirrors a SELL larger than the broker holding (the mirror still submits — `guard_sells=False` — so the broker's rejection or short is the evidence), and `AlpacaBroker` writes concise rejection/error details on failed submits.
- If the status write fails after Alpaca accepted an order (leaving `alpaca_status IS NULL`), or if a client timeout hit after Alpaca accepted (`alpaca_status = 'ERROR'` with `alpaca_order_id IS NULL`), `sync_alpaca_orders.py` batch-fetches recent orders via `get_orders(status=ALL, after=...)` (falling back to `get_order_by_client_id` / `get_order_by_id` only if truncated) and re-attaches them by deterministic `client_order_id` — recovery, never re-submission. Because non-mirrored lanes now stamp `NO_MIRROR` at insert time (and `supabase/migrations/20261126140000_enforce_alpaca_state_machine_and_no_mirror.sql` backfilled structural non-mirrored `NULL`s), repair directly queries recent `NULL` and `ERROR` rows **newest-first** without `owner_id` prefix heuristics, writes `alpaca_submitted_at` alongside the status (plus `alpaca_filled_at` with UTC fallback if `FILLED`, clearing stale transient error `alpaca_note` on recovery), and updates with compare-and-set (`.is_("alpaca_status","null")`, `.eq("alpaca_status","ERROR")`, and `.eq("alpaca_status","SUBMITTED")` in `sync_orders`) backed by PostgreSQL cross-column CHECK (`trades_alpaca_columns_check`) and transition trigger (`trg_enforce_trades_alpaca_status_transition`). A repair failure is caught and logged so it can never abort the reconciliation that follows; a 404 counts as `skipped`. `_update_trade` returns `True`/`False`, the submit result carries `persisted`, and `_mirror_to_alpaca`'s retry writes the same full column set (`alpaca_status`, `alpaca_order_id`, `alpaca_submitted_at`) — a partial payload there would create a SUBMITTED row the reconciler can never see, since that pass filters on `alpaca_submitted_at`.
- `guard_sells=True` by default: a SELL with no broker position is skipped (`SKIPPED_NO_POSITION`) or capped to the held quantity, because the paper account allows shorting and an unguarded oversell would open a short. The live SPY trader passes `guard_sells=False` deliberately — its ledger is authoritative and the broker rejection is the audit record.
- `alpaca_submitted_at` is written as an explicit UTC ISO timestamp by both `_update_trade` and the mirror retry, never the `'now()'` string: Postgres does accept `'now()'` as a `timestamptz` literal, but a literal that only works because the parser tolerates the parentheses is not something to leave in an audit column.
- `try_get_alpaca_position(ticker) -> float | None` is the evidence-grade read: `None` when the broker cannot answer, `0.0` only for a genuine 404. `get_alpaca_position` still collapses every failure to `0.0`, which is correct for the SELL guard ("cannot ask" ⇒ "do not sell") and wrong for anything recorded on a row.
- The constructor accepts `client` and `sb_client` for hermetic tests; `_update_trade` writes `alpaca_status`, `alpaca_submitted_at`, and `alpaca_order_id` onto the ledger trade row.
- The daemon builds its own `TradingClient` in `_create_clients` (`apps/engine/trading/runner.py`) — once, with `paper=True`, and only when `ALPACA_ENABLED` — then injects it as `AlpacaBroker(client=...)`. Injection does not bypass the kill switch: `AlpacaBroker.__init__` checks `ALPACA_ENABLED` before accepting an injected client, so a caller that constructs its own client still cannot mirror while the flag is off. The broker's own construction path stays live for the other trading lanes and now degrades to "no mirror" on a construction error instead of aborting the caller's startup. `test_create_clients_honours_the_alpaca_kill_switch` and the `paper=True` assertion in `test_create_clients_initializes_when_keys_present` pin both.
- `sync-alpaca.yml` reconciles `SUBMITTED` rows every 15 minutes across the session (13:00–21:45 UTC weekdays) to `FILLED` / `REJECTED` / `CANCELED` / `EXPIRED`.
- `NO_MIRROR` is stamped at insert time on structurally non-mirrored ledger trades (`daily_live_trading.py` `SHORT`/`COVER`, `daily_bond_trading.py` entry/exit legs, `stock_picks_trading.py` `SHORT`/`SELL`/`COVER`, `sector_trading.py` `SHORT`/`COVER`, `system_portfolios.py`, `daily_trading.py` default, `Portfolio.execute_trade(..., skip_alpaca_mirror=True)` via `execute_portfolio_trade(..., p_alpaca_status='NO_MIRROR')`, and the backtest sandbox's local `execute_sqlite_portfolio_trade`) as well as backfilled historical non-mirrored / silent-window trades.

## Repair & Sync Pass Mechanics (`apps/engine/scripts/sync_alpaca_orders.py`)

The reconciler runs two passes in one invocation: **repair** (re-attach an order id to a row whose status write failed) and **sync** (advance `SUBMITTED` rows to a terminal state).

### Batch order prefetch (`_fetch_batch_orders`)

One `GetOrdersRequest(status=QueryOrderStatus.ALL, after=cutoff, limit=500)` call is issued before either pass, returning `(by_id, by_client_id, is_complete)`. `is_complete` is true only for a non-truncated list (`len(orders) < 500`); an exception or a non-list response yields `({}, {}, False)`, which forces the per-order lookup path. Both passes prefer the batch maps over per-trade SDK calls, so a normal run performs one broker round-trip instead of N+1.

### Repair candidates (`_fetch_repair_candidates`)

Two newest-first queries inside `REPAIR_MAX_AGE_HOURS` (24 h), each capped at `REPAIR_LIMIT` (100): `alpaca_status IS NULL` rows, and `alpaca_status = 'ERROR'` rows with `alpaca_order_id IS NULL` (selecting `alpaca_note` so a recovered transient error note can be cleared). The `ERROR` query uses `.filter("alpaca_status", "eq", "ERROR")` rather than `.eq(...)` so it does not disturb the `SUBMITTED` query's `eq` chain, which tests assert on.

### Repair path

For each candidate the deterministic `client_order_id` (`{owner_id}__{ticker}__{signal}__{trade_id}`) is resolved in this order: batch `by_client_id` → skip when the batch was complete (genuinely absent on the broker) → `get_order_by_client_id` (404 = `skipped`, API/unexpected error = `errors`). The payload is only built for a mapped broker state (terminal or open), maps the broker status to `FILLED`/`CANCELED`/`EXPIRED`/`REJECTED` or `SUBMITTED`, stamps an explicit UTC `alpaca_submitted_at`, adds `alpaca_filled_at` (order `filled_at`, else UTC now) when `FILLED`, and clears a previous transient `alpaca_note` on `ERROR` recovery unless it starts with `BROKER_POSITION_MISMATCH`. Persistence is compare-and-set — `.is_("alpaca_status", "null")` for NULL candidates, `.eq("alpaca_status", "ERROR")` for ERROR candidates — and a zero-row update counts as `skipped` (another writer got there first).

### Sync path

The terminal transition update is also compare-and-set on `.eq("alpaca_status", "SUBMITTED")`; a zero-row result increments `skipped` and logs at debug instead of double-counting a concurrent transition. `alpaca_filled_at` falls back to the current UTC timestamp when the broker reports `FILLED` without a `filled_at`, so a `FILLED` row always satisfies `trades_alpaca_columns_check`. `OPEN_ORDER_STATUSES` is derived from the SDK enum (`{s.value for s in OrderStatus}` minus `TERMINAL_STATUSES`) rather than a hand-maintained literal set, so a new Alpaca status is treated as pending instead of unmapped.

## Terminal Report

The `render_terminal_report()` method produces a structured Unicode-box report with four sections:
- Executive Summary & Performance Verification
- Positions Reconciliation
- Recent Trades & Execution Slippage (last 10)
- Discrepancies & Root-Cause Anomalies

## CLI Usage

```sh
# Default audit for MiniMax-M3.1-Flash over 7 days
python main.py audit-alpaca

# Audit a specific model with custom lookback
python main.py audit-alpaca --model claude-haiku-5-5 --days 30

# JSON output for programmatic consumption
python main.py audit-alpaca --model gpt-6-luna --days 14 --json
```

## Related

- [[concepts/alpaca-order-sync]]
- [[concepts/external-order-attestation]]
- [[concepts/state-machines]] — the `trades.alpaca_status` state machine, cross-column CHECK, and transition trigger
- [[concepts/atomic-trade-execution]] — the `execute_portfolio_trade` RPC that accepts `p_alpaca_status`
- [[entities/engine]]
- [[entities/database]]
