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
| Staleness | JIT price vs prompt-injected ≤ 2% |
| Buying Power | Cost fits within Reg T limits |
| Minimum Value | Trade cost above floor |
| SMA Floor | Projected SMA above safety threshold |

## Reg T Margin

Validates Initial Margin, Maintenance Margin, Buying Power, and SMA. 10% minimum
position rule enforced by quantity calculation tools.

## Trade Settlement

"Commit at the End" atomic pattern: save decision → UPSERT position → INSERT
trade → update cash/SMA. Prevents phantom deductions on DB failure. Alpaca paper
mirroring via fire-and-forget DAY limit orders.

## Attribution Locking

Two-phase commit: pre-trade decision save assigns `decision_id`, trade executes
with FK, post-trade status = EXECUTED. Result: `News → Reasoning → Decision ↔ Trade`.

## Rejection Preservation

Every rejection is saved with a status code. Types: MARGIN, OWNERSHIP,
REDUNDANCY, TOOL_USAGE, VERIFICATION, HALLUCINATION, LIQUIDITY, MARKET_CLOSED,
STALE_QUOTE, ERROR_PROVIDER.

## Related

- [[entities/pipeline]]
- [[concepts/consensus]]
- [[concepts/tool-enforcement]]
