---
tags: [minimax, execution, market-order, buffer]
category: concept
---

# MiniMax Portfolio

MiniMax-M3 uses a simplified execution model that bypasses the standard limit-order pipeline. Instead of placing native limit orders, the engine submits a **market order** with a ±0.5% price buffer to account for slippage. The executed price (`exec_price`) is the market price adjusted by this buffer.

## Alpaca Mirror Orders

For each MiniMax market order, a corresponding limit order is placed on the Alpaca brokerage. The limit price is set to the same buffered `exec_price` — **no additional buffer is applied**. This ensures the Alpaca mirror matches the simulated execution exactly, avoiding the double-buffer bug that previously inflated limit prices.

## Rationale

MiniMax-M3 does not support native function calling for order placement, so the engine parses raw JSON decisions and executes them directly. The market order with buffer provides a pragmatic fallback that still respects risk limits and Reg T constraints.

## Related

- [[entities/pipeline]]
- [[concepts/execution]]
- [[concepts/tool-enforcement]]
