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

## Margin & Sizing Hazards

Because MiniMax-M3 bypasses standard verifier tool loops and JIT checks, it does not dynamically downsize its allocations based on real-time feedback. 

* **The Sizing Risk**: If MiniMax signals a `BUY` with a high allocation percentage (e.g., 100% of available buying power), the engine sizes the transaction using gross leveraged buying power (4x excess liquidity).
* **The Violation**: Highly leveraged purchases generate a massive margin loan (since the actual cash balance is much lower). Under Regulation T, this trade reduces the Special Memorandum Account (SMA) by 57% of the total cost. This reduction easily wipes out the SMA balance, driving it below the mandatory **10% SMA-to-equity floor** and resulting in an immediate `REJECTED_MARGIN` status.
* **Mitigation**: When MiniMax suggests purchases, it should specify a low `allocation_percentage` (e.g. 5–30% of buying power) to stay within the SMA compliance floor.

## Related

- [[entities/pipeline]]
- [[concepts/execution]]
- [[concepts/tool-enforcement]]

