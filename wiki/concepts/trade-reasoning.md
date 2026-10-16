---
tags: [execution, auditability, trades]
category: concept
---

# Trade Reasoning

Every trade executed through `Portfolio.execute_trade` can carry an optional `reason` string that is persisted to the trade record's `reasoning` column. This records the catalyst or justification behind a trade, supporting the platform's information auditability tenet — any position can be traced back to the thesis that motivated it.

## Behavior

`execute_trade(..., reason: str | None = None)` — when `reason` is provided, it is written into the trade's `reasoning` field alongside `ticker`, `quantity`, `price`, and `signal`. Portfolios such as `sys-future-forces` pass reasons like `future_force_buy: Autonomous Defense` so each buy can be traced to the force that motivated it.

## Related

- [[concepts/auditability]] — full traceability of data, metrics, and trades
- [[concepts/execution]] — pre-market validation, Reg T checks, trade settlement
