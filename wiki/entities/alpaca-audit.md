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

- `submit_market_order(...)` / `submit_limit_order(...)` return `{"status": str, "order_id": str | None}` where status is `SUBMITTED`, `ERROR`, `SKIPPED_NO_POSITION`, or `DISABLED` (no client / missing keys). Callers that ignore the return value are unaffected.
- `trades.alpaca_note` carries divergence detail that must not overload the status: the live trader stamps `BROKER_POSITION_MISMATCH (ledger N, broker M)` when it mirrors a SELL larger than the broker holding (the mirror still submits — `guard_sells=False` — so the broker's rejection or short is the evidence).
- If the status write fails after Alpaca accepted an order, the row keeps a NULL `alpaca_order_id`. `sync_alpaca_orders.py` re-attaches it by looking the order up with the deterministic `client_order_id` — recovery, never re-submission. The repair pass looks back 24 hours, scans **newest-first** (a backlog beyond `REPAIR_LIMIT=100` would otherwise starve the row that just failed), writes `alpaca_submitted_at` alongside the status (without it the reconciler could never advance the row), and updates with a `.is_("alpaca_status","null")` compare-and-set so it cannot clobber a concurrent sync. A repair failure is caught and logged so it can never abort the reconciliation that follows; a 404 counts as `skipped`. `_update_trade` returns `True`/`False`, the submit result carries `persisted`, and `_mirror_to_alpaca`'s retry writes the same full column set (`alpaca_status`, `alpaca_order_id`, `alpaca_submitted_at`) — a partial payload there would create a SUBMITTED row the reconciler can never see, since that pass filters on `alpaca_submitted_at`.
- `guard_sells=True` by default: a SELL with no broker position is skipped (`SKIPPED_NO_POSITION`) or capped to the held quantity, because the paper account allows shorting and an unguarded oversell would open a short. The live SPY trader passes `guard_sells=False` deliberately — its ledger is authoritative and the broker rejection is the audit record.
- `alpaca_submitted_at` is written as an explicit UTC ISO timestamp by both `_update_trade` and the mirror retry, never the `'now()'` string: Postgres does accept `'now()'` as a `timestamptz` literal, but a literal that only works because the parser tolerates the parentheses is not something to leave in an audit column.
- `try_get_alpaca_position(ticker) -> float | None` is the evidence-grade read: `None` when the broker cannot answer, `0.0` only for a genuine 404. `get_alpaca_position` still collapses every failure to `0.0`, which is correct for the SELL guard ("cannot ask" ⇒ "do not sell") and wrong for anything recorded on a row.
- The constructor accepts `client` and `sb_client` for hermetic tests; `_update_trade` writes `alpaca_status`, `alpaca_submitted_at`, and `alpaca_order_id` onto the ledger trade row.
- `sync-alpaca.yml` reconciles `SUBMITTED` rows every 15 minutes across the session (13:00–21:45 UTC weekdays) to `FILLED` / `REJECTED` / `CANCELED` / `EXPIRED`.
- `NO_MIRROR` is a backfilled historical marker for trades that executed in the ledger while the mirror was silently failing (the 7 `live-spy-trader` trades between `2026-11-24T19:27Z` and `2026-11-25T16:59Z`); it is never written at runtime.

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
- [[entities/engine]]
- [[entities/database]]
