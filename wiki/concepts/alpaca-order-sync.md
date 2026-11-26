---
tags: [execution, alpaca, broker, order-sync, guardrails]
category: concept
---

# Alpaca Order Sync

The engine mirrors its internal trade ledger to the Alpaca paper broker via `AlpacaBroker` (`apps/engine/execution/alpaca_broker.py`). Both limit orders (`submit_limit_order`) and market orders (`submit_market_order`) map an engine-level **signal** string onto an Alpaca `OrderSide` and apply position-aware guardrails before submitting.

## Signal → OrderSide Mapping

Signal strings are normalized to uppercase and mapped as follows:

| Signal | OrderSide |
|--------|-----------|
| `BUY`, `LONG`, `COVER` | `BUY` |
| `SELL`, `SHORT` | `SELL` |
| any other (fallback) | `BUY` if the string contains `BUY`, else `SELL` |

This lets the engine express intentional shorts (`SHORT`) and closes of shorts (`COVER`) distinctly from ordinary long closes (`SELL`), while the fallback preserves older signal names.

## Position Guardrails

Guardrails ensure the engine never accidentally opens (or fails to close) a position that Alpaca does not physically hold.

### SELL — closing a long

A `SELL` is only allowed to close long shares that Alpaca **physically holds**:

- If `get_alpaca_position(ticker) <= 0`, the order is skipped and the trade is marked `SKIPPED_NO_POSITION`. The engine does **not** fall back to the Supabase ledger to synthesize a position — selling shares Alpaca does not hold would open an unintended short and collide with subsequent `BUY` orders (403 errors).
- If the requested quantity exceeds Alpaca's holdings, it is capped to `int(alpaca_qty)`.

### COVER — closing a short

A `COVER` is only allowed when Alpaca is actually short the ticker:

- If `get_alpaca_position(ticker) >= 0`, the order is skipped and marked `SKIPPED_NO_POSITION` (cannot cover without a short position).
- If the requested quantity exceeds the absolute short size, it is capped to `int(abs(alpaca_qty))`.

### SHORT

A `SHORT` maps to a `SELL` and bypasses the position guardrail entirely — it is an intentional short entry, so it proceeds even when Alpaca holds zero shares.

## Position Reads: `get_alpaca_position` vs `try_get_alpaca_position`

Two readers exist because the guard and the audit trail need different failure semantics:

- **`get_alpaca_position(ticker) -> float`** — collapses every failure (no client, API error, unparseable `qty`) to `0.0`. That is correct for the SELL/COVER guard, where "cannot ask" and "flat" both mean "do not sell".
- **`try_get_alpaca_position(ticker) -> float | None`** — returns `None` when the broker cannot answer, `0.0` only for a genuine `404` (no position), and the parsed quantity otherwise. Callers that record *evidence* must use this, because a failed read must never be written down as a 0-share book. `apps/engine/trading/intraday_portfolio.py` uses it to stamp `BROKER_POSITION_MISMATCH (ledger N, broker M)` onto `trades.alpaca_note` only when the broker genuinely holds fewer shares than the ledger is selling.

## Return Values & `guard_sells`

Both submit methods return the outcome instead of `None`, so the caller can record what the mirror actually reported:

| Result | Meaning |
| :--- | :--- |
| `{"status": "SUBMITTED", "order_id": str, "persisted": bool}` | Alpaca accepted the order. `persisted` is `False` when the ledger row write failed, so the caller can retry it once. |
| `{"status": "ERROR", "order_id": None, "persisted": bool}` | The submission raised (e.g. `403 insufficient buying power`). |
| `{"status": "SKIPPED_NO_POSITION", "order_id": None}` | The position guardrail rejected the order. |
| `{"status": "DISABLED", "order_id": None}` | No client (missing keys or `ALPACA_ENABLED` off) — the mirror was never attempted. |

`guard_sells` (default `True`) controls the SELL/COVER position guardrails. The live SPY trader passes `guard_sells=False` deliberately: its ledger is authoritative, so the mirror submits the full ledger quantity and a broker rejection (or an unintended short on the shared paper account) becomes the audit record. Every other lane keeps the default short-prevention behaviour.

The constructor accepts `client` and `sb_client` for hermetic tests, exposes the underlying paper `TradingClient` through a `client` property, and `_update_trade` returns `True`/`False` so a failed row write is visible rather than silent.

## Trade Status Flags

Skipped orders are recorded via `_update_trade` with the sentinel status `SKIPPED_NO_POSITION`, giving a full audit trail of signals that were rejected because the broker-side position did not support them. `DISABLED` (mirror never attempted) and `ERROR` (attempted and failed) are deliberately distinct states, and `SUBMITTED` rows are reconciled to `FILLED` / `REJECTED` / `CANCELED` / `EXPIRED` by `apps/engine/scripts/sync_alpaca_orders.py` (see [[entities/alpaca-audit]]).

`trades.alpaca_note` (migration `20261126000000_add_alpaca_note_to_trades.sql`) carries free-text mirror audit detail — e.g. `BROKER_POSITION_MISMATCH (ledger 2, broker 1)` — deliberately separate from `alpaca_status`, which carries the order outcome. It is never used for state.

## Reconciliation Cadence

`.github/workflows/sync-alpaca.yml` runs every 15 minutes across the US session (`*/15 13-21 * * 1-5`, covering 09:30–16:00 ET in both EDT and EST) so a rejected order does not read `SUBMITTED` until after the close. The workflow declares `concurrency: { group: sync-alpaca, cancel-in-progress: false }`, so a manual dispatch cannot overlap the scheduled run — the repair pass is a compare-and-set, but two concurrent full syncs would still double-poll Alpaca.

## Related

- [[entities/engine]]
- [[concepts/execution]]
- [[entities/sector-trading]]
- [[entities/alpaca-audit]] — the reconciliation pipeline and mirror contract
- [[concepts/external-order-attestation]] — why the ledger mirrors to Alpaca at all
