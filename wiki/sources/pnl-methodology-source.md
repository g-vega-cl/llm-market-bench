---
tags: [engine, pnl, calculation]
category: source
---

# Source: P&L Calculation Methodology

Synthesized from `raw/docs/engine/PNL-CALCULATIONS.md`.

## Takeaways

- **Weighted Average Cost**: The system uses a weighted average for cost basis. New purchases update the average; partial sales realize P&L without changing the cost basis of remaining shares.
- **Real-Time P&L View**: A database view (`position_pnl`) calculates unrealized P&L on-the-fly by joining current market prices with the portfolio ledger.
- **Zero-Cost Handling**: Explicit logic to handle edge cases like stock grants or warrants to avoid division-by-zero errors.

## Related

- [[entities/engine]]
- [[entities/database]]
- [[concepts/execution]]
