---
tags: [source, reg-t, margin, calculations]
category: source
source: docs/engine/account-buying-power-reg-t4-calculations.md
---

# Source: Reg T Margin Account Calculations

Reference for Regulation T margin calculations. All scenarios assume $10,000 initial deposit.

Key details:

- **Core metrics**: NLV (Cash + MVS), Initial Margin (MVS × 57%), Maintenance Margin (MVS × 33%), Excess Liquidity (NLV - MM), Available Funds (NLV - IM), Buying Power (Available Funds × 4), SMA (Reg T credit line)
- **SMA rules**: Does not decrease from market drops (only withdrawals/purchases), market gains increase SMA at EOD if (ELV - 57% MVS) > current SMA, must be ≥ 0 or broker liquidates
- **Internal guardrail**: Projected SMA must remain ≥ 10% of total equity or trade rejected
- **Three worked scenarios**: near-full cash, leveraged at a loss, multi-asset mixed performance
