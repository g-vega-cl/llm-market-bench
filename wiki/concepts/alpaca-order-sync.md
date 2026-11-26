---
tags: [execution, alpaca, broker, order-sync, guardrails]
category: concept
---

# Alpaca Order Sync

The engine mirrors its internal trade ledger to the Alpaca paper broker via `AlpacaBroker` (`apps/engine/execution/alpaca_broker.py`). Both limit orders (`submit_limit_order`) and market orders (`submit_market_order`) are thin wrappers over one shared `_submit_order` path that maps an engine-level **signal** string onto an Alpaca `OrderSide`, applies position-aware guardrails, submits, and records the outcome on the trade row.

## Signal → OrderSide Mapping

`_resolve_order_side(signal)` normalizes the signal to uppercase and maps it as follows:

| Signal | OrderSide |
|--------|-----------|
| `BUY`, `LONG`, `COVER` | `BUY` |
| `SELL`, `SHORT` | `SELL` |
| any other (fallback) | `BUY` if the string contains `BUY`, else `SELL` |

This lets the engine express intentional shorts (`SHORT`) and closes of shorts (`COVER`) distinctly from ordinary long closes (`SELL`), while the fallback preserves older signal names.

## Position Guardrails

`_apply_position_guardrail(trade_id, ticker, quantity, sig)` runs before submission (only when `guard_sells` is true and the signal is `SELL` or `COVER`) and ensures the engine never accidentally opens (or fails to close) a position that Alpaca does not physically hold.

### SELL — closing a long

A `SELL` is only allowed to close long shares that Alpaca **physically holds**:

- If `get_alpaca_position(ticker) <= 0`, the order is skipped and the trade is marked `SKIPPED_NO_POSITION`. The engine does **not** fall back to the Supabase ledger to synthesize a position — selling shares Alpaca does not hold would open an unintended short and collide with subsequent `BUY` orders (403 errors).
- If the requested quantity exceeds Alpaca's holdings, it is capped to `int(alpaca_qty)`.
- A fractional holding below one whole share (e.g. `0.5`) yields `available = 0`, so the order is skipped as `SKIPPED_NO_POSITION` rather than submitting a zero-quantity order.

### COVER — closing a short

A `COVER` is only allowed when Alpaca is actually short the ticker:

- If `get_alpaca_position(ticker) >= 0`, the order is skipped and marked `SKIPPED_NO_POSITION` (cannot cover without a short position).
- If the requested quantity exceeds the absolute short size, it is capped to `int(abs(alpaca_qty))`.

### SHORT

A `SHORT` maps to a `SELL` and bypasses the position guardrail entirely — it is an intentional short entry, so it proceeds even when Alpaca holds zero shares.

## Position Reads: `get_alpaca_position` vs `try_get_alpaca_position`

Two readers exist because the guard and the audit trail need different failure semantics:

- **`get_alpaca_position(ticker) -> float`** — delegates to `try_get_alpaca_position` and collapses every failure (no client, API error, unparseable `qty`) to `0.0`. That is correct for the SELL/COVER guard, where "cannot ask" and "flat" both mean "do not sell".
- **`try_get_alpaca_position(ticker) -> float | None`** — returns `None` when the broker cannot answer, `0.0` only for a genuine `404` (no position), and the parsed quantity otherwise. Callers that record *evidence* must use this, because a failed read must never be written down as a 0-share book. `apps/engine/trading/intraday_portfolio.py` uses it to stamp `BROKER_POSITION_MISMATCH (ledger N, broker M)` onto `trades.alpaca_note` only when the broker genuinely holds fewer shares than the ledger is selling.

## Return Values & `guard_sells`

Both submit methods return the outcome instead of `None`, so the caller can record what the mirror actually reported:

| Result | Meaning |
| :--- | :--- |
| `{"status": "SUBMITTED", "order_id": str, "persisted": bool}` | Alpaca accepted the order. `persisted` is `False` when the ledger row write failed, so the caller can retry it once. |
| `{"status": "REJECTED", "order_id": None, "persisted": bool}` | Alpaca rejected the request with a terminal 4xx `APIError` (e.g. `403` insufficient buying power); the formatted reason is recorded in `trades.alpaca_note`. |
| `{"status": "ERROR", "order_id": None, "persisted": bool}` | Submission failed with a 5xx `APIError`, a retryable 4xx (`408`, `429`, or `422` naming `client_order_id`), a timeout, or an unexpected exception; the formatted reason is recorded in `trades.alpaca_note` so repair can recover accepted orders. |
| `{"status": "SKIPPED_NO_POSITION", "order_id": None}` | The position guardrail rejected the order. |
| `{"status": "DISABLED", "order_id": None}` | No client (missing keys or `ALPACA_ENABLED` off) — the mirror was never attempted. The trade row is stamped `DISABLED` (see below). |

`guard_sells` (default `True`) controls the SELL/COVER position guardrails. The live SPY trader passes `guard_sells=False` deliberately: its ledger is authoritative, so the mirror submits the full ledger quantity and a broker rejection (or an unintended short on the shared paper account) becomes the audit record. Every other lane keeps the default short-prevention behaviour.

The constructor accepts `client` and `sb_client` for hermetic tests, exposes the underlying paper `TradingClient` through a `client` property, and `_update_trade` returns `True`/`False` so a failed row write is visible rather than silent.

## Error Classification & `alpaca_note`

`_is_terminal_rejection(exc)` decides whether an `APIError` is a terminal broker refusal or a recoverable failure:

- A `4xx` status is **terminal** (`REJECTED`) unless it is `408` (request timeout), `429` (rate limit), or `422` whose message names `client_order_id` (a duplicate-id collision that repair can resolve). Those three stay `ERROR` so `sync_alpaca_orders.py` can recover them.
- Any non-4xx status (5xx, timeouts, unexpected exceptions) is `ERROR`.

`_format_alpaca_error(exc)` renders a concise single-line reason — `HTTP <code>: <message>` when a status code is present, otherwise `<ExceptionType>: <message>` — truncated to `_MAX_NOTE_LEN` (240 chars) and written to `trades.alpaca_note` via `_update_trade(..., note=...)`. `alpaca_note` is free-text mirror audit detail, deliberately separate from `alpaca_status`, which carries the order outcome; it is never used for state.

## `_update_trade` and the `DISABLED` Stamp

`_update_trade(trade_id, order_id, status, note=None)` writes `alpaca_status`, conditionally `alpaca_order_id`, conditionally `alpaca_note`, and — for every status **except** `DISABLED` — `alpaca_submitted_at` (an explicit UTC ISO timestamp). `DISABLED` omits `alpaca_submitted_at` because no order was ever sent to Alpaca, so the reconciler (which filters on `alpaca_submitted_at`) never tries to advance a row that has no broker order. The Supabase write is offloaded via `asyncio.to_thread`.

## Kill Switch & Construction Failure

`ALPACA_ENABLED` is evaluated **before** an injected `client` is accepted, so a caller that builds its own `TradingClient` cannot mirror while the flag is off. `apps/engine/trading/runner.py` mirrors the rule on its side: `_create_clients` constructs the paper `TradingClient` only when `ALPACA_ENABLED` is true, while the read-only `StockHistoricalDataClient` is built regardless (market data is read-only and stays available).

A `TradingClient` construction failure is caught and logged with `logger.exception`, leaving `_client = None` so the broker degrades to `DISABLED` instead of aborting the caller's startup — ten trading lanes share this path and the ledger does not need the mirror.

## Async Offloading

Every blocking Alpaca SDK call and Supabase write is wrapped in `asyncio.to_thread`: `submit_order`, `get_orders`, `cancel_order_by_id`, the position reads, and the `trades` row update. The broker therefore never blocks the event loop of the trading daemon that shares it with the tape poller and the other concurrent loops.

## Trade Status Flags

Skipped orders are recorded via `_update_trade` with the sentinel status `SKIPPED_NO_POSITION`, giving a full audit trail of signals that were rejected because the broker-side position did not support them. `DISABLED` (mirror never attempted) and `ERROR` (attempted and failed) are deliberately distinct states, and `SUBMITTED` rows are reconciled to `FILLED` / `REJECTED` / `CANCELED` / `EXPIRED` by `apps/engine/scripts/sync_alpaca_orders.py` (see [[entities/alpaca-audit]]).

`trades.alpaca_note` (`supabase/migrations/20261126000000_add_alpaca_note_to_trades.sql`) carries free-text mirror audit detail — e.g. `BROKER_POSITION_MISMATCH (ledger 2, broker 1)` or the HTTP rejection/error reason from `AlpacaBroker` — deliberately separate from `alpaca_status`, which carries the order outcome. It is never used for state. Both `submit_market_order` and `submit_limit_order` share `_submit_order`, persist `DISABLED` when `_client` is absent, offload blocking Alpaca SDK calls onto `asyncio.to_thread`, and are backed by PostgreSQL state-machine guards: `trades_alpaca_status_check` (`supabase/migrations/20261126120000_add_alpaca_status_check.sql`), `trades_alpaca_columns_check` cross-column invariants, and the `trg_enforce_trades_alpaca_status_transition` transition trigger (`supabase/migrations/20261126140000_enforce_alpaca_state_machine_and_no_mirror.sql`). Non-mirrored lanes stamp `NO_MIRROR` at insert time directly (including `Portfolio.execute_trade(..., skip_alpaca_mirror=True)` via `execute_portfolio_trade(..., p_alpaca_status='NO_MIRROR')`).

## Reconciliation Cadence

`.github/workflows/sync-alpaca.yml` runs every 15 minutes across the US session (`*/15 13-21 * * 1-5`, covering 09:30–16:00 ET in both EDT and EST) so a rejected order does not read `SUBMITTED` until after the close. The workflow declares `concurrency: { group: sync-alpaca, cancel-in-progress: false }`, so a manual dispatch cannot overlap the scheduled run — the repair pass is a compare-and-set, but two concurrent full syncs would still double-poll Alpaca.

## Related

- [[entities/engine]]
- [[concepts/execution]]
- [[entities/sector-trading]]
- [[entities/alpaca-audit]] — the reconciliation pipeline and mirror contract
- [[concepts/external-order-attestation]] — why the ledger mirrors to Alpaca at all
