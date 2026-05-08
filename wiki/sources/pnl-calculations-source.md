---
tags: [source, pnl, calculations, portfolio]
category: source
source: docs/engine/PNL-CALCULATIONS.md
---

# Source: P&L Calculation Methodology

Weighted average cost basis for tracking P&L.

Key details:

- BUY: `New Avg = (Old Total Cost + New Cost) / New Total Quantity`
- Unrealized P&L: `(Current Price - Avg Cost) × Quantity`
- Realized P&L: `(Sell Price - Avg Cost) × Quantity Sold`
- Partial sales: avg cost basis of remaining shares unchanged
- SQL view `position_pnl` for live unrealized P&L
- Zero cost basis handled as full sale proceeds, 0% returned
- Full audit trail: `News → Reasoning → Decision ↔ Trade → P&L`
