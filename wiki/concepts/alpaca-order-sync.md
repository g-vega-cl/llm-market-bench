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

## Trade Status Flags

Skipped orders are recorded via `_update_trade` with the sentinel status `SKIPPED_NO_POSITION`, giving a full audit trail of signals that were rejected because the broker-side position did not support them.

## Related

- [[entities/engine]]
- [[concepts/execution]]
- [[entities/sector-trading]]
