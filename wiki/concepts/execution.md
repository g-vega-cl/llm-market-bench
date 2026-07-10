---
tags: [execution, validation, trades, settlement]
category: concept
---

# Execution & Trade Settlement

Validates and executes trades with defense-in-depth guardrails.

## Pre-Market Validation

| Guardrail | Logic |
|-----------|-------|
| Existence | Ticker found via FMP |
| Liquidity | Market cap above floor |
| Staleness | JIT price vs prompt-injected ≤ 2% (Bypassed for MiniMax) |
| Buying Power | Cost fits within Reg T limits |
| Minimum Value | Trade cost above floor |
| SMA Floor | Projected SMA above safety threshold |

## Reg T Margin

Validates Initial Margin, Maintenance Margin, Buying Power, and SMA. 10% minimum
position rule enforced by quantity calculation tools.

## Trade Settlement

"Commit at the End" atomic pattern: save decision → UPSERT position → INSERT
trade → update cash/SMA. Prevents phantom deductions on DB failure. Alpaca paper
mirroring via fire-and-forget DAY limit orders (or mirror limit orders set to the buffered execution price for MiniMax's simulated market orders).

- **MiniMax Simplified Execution**: Rather than placing standard limit orders, the MiniMax portfolio places JIT simulated **Market Orders** using a **±0.5% slippage buffer** (BUY = `price * 1.005`, SELL = `price * 0.995`). Bypasses the verifier, stale price checks, tool loops, and semantic redundancy checks. Hard stops still apply for unheld short-selling (capped to held position size).

## Attribution Locking

Two-phase commit: pre-trade decision save assigns `decision_id`, trade executes with FK (`trades.decision_id`), and post-trade status is updated to `EXECUTED` with `decisions.trade_id` set. 

Result: Bidirectional linking `News → Reasoning → Decision ↔ Trade`.
* **Forward Link**: `decisions.trade_id` points to the primary trade record.
* **Backward Link**: `trades.decision_id` points back to the initiating decision.

> [!NOTE]
> **Historical Database Anomaly (Feb/Mar 2026)**: Early pipeline code failed to populate the backward reference `trades.decision_id` at execution time, leaving it as `NULL` despite the forward reference being locked. This triggered system audits for "Executed Decisions Without Trade Record". A retroactive database repair script was run to restore referential integrity by populating the missing `decision_id` values for these 13 historical trades. Current execution code correctly populates both links atomically.

## Rejection Preservation

Every rejection is saved with a status code. Types: MARGIN, OWNERSHIP,
REDUNDANCY, TOOL_USAGE, VERIFICATION, HALLUCINATION, LIQUIDITY, MARKET_CLOSED,
STALE_QUOTE, ERROR_PROVIDER, REJECTED_OWNERSHIP.

## Related

- [[entities/pipeline]]
- [[concepts/consensus]]
- [[concepts/tool-enforcement]]
- [[concepts/minimax-portfolio]]
