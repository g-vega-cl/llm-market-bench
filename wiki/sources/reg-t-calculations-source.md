---
tags: [engine, margin, validation]
category: source
---

# Source: Reg T Margin Account Calculations

Synthesized from `raw/docs/engine/account-buying-power-reg-t4-calculations.md`.

## Takeaways

- **Margin Guardrails**: The system strictly follows Regulation T rules for Initial Margin (57%) and Maintenance Margin (33%).
- **SMA Stability**: SMA does not decrease with market drops, providing a buffer, but must be $\ge 0$ at end-of-day to avoid liquidation.
- **Internal Safety Floor**: An additional 10% SMA-to-equity floor is enforced to prevent over-leveraging before the broker's hard limit is reached.
- **Minimum Trade Value**: Trades must be $\ge \$1,000$ or $10\%$ of equity (whichever is higher) to ensure meaningful position sizing.

## Related

- [[entities/engine]]
- [[concepts/execution]]
- [[concepts/tool-enforcement]]
