# Reg T Margin Account Calculations

Reference for **IBKR Reg T Margin Account** calculations. All scenarios assume an initial deposit of **$10,000 USD**.

## Core Formulas

| Metric | Formula | Purpose |
|--------|---------|---------|
| **Net Liquidation Value (NLV)** | `Cash + Market Value of Securities` | Total account value |
| **Realized Value** | `Cash + Total Cost Basis` | NLV excluding unrealized P/L |
| **Equity with Loan Value (ELV)** | Same as NLV for marginable stocks | Collateral for margin loan |
| **Initial Margin (IM)** | `MVS × 57%` | Reg T cost to open a position |
| **Maintenance Margin (MM)** | `MVS × 33%` | Min equity to avoid liquidation |
| **Excess Liquidity** | `NLV - MM` | Safety margin for existing positions |
| **Available Funds** | `NLV - IM` | Capacity for new trades |
| **Buying Power** | `Available Funds × 4` | Intraday purchase capacity |
| **SMA** | `Max(Prior SMA + ∆Cash - IM_trades, NLV - (MVS × 0.57))` | Reg T credit line |

## SMA Key Rules

- SMA does **not** decrease from market price drops — only from withdrawals or new purchases
- Market gains increase SMA at end of day if `(ELV - 57% MVS) > current SMA`
- End-of-day SMA must be ≥ 0 or IBKR liquidates positions
- **Internal guardrail**: Projected SMA must remain ≥ 10% of total equity or trade is rejected

## System Guardrails

| Rule | Value |
|------|-------|
| SMA Floor | ≥ 10% of Total Equity |
| Minimum Trade Value | max($1,000, 10% × Total Equity); waived for SELL via tool |
| Market Data Fallback | Falls back to `average_cost_basis` if current prices unavailable |

## Worked Scenarios

### Scenario 1: Near-Full Cash ($9,950 in QQQ, $10K deposit)

| Metric | Value |
|--------|-------|
| Cash | $49.76 |
| MVS | $9,950.24 |
| NLV | $10,000.00 |
| IM | $5,671.64 |
| MM | $3,283.58 |
| Excess Liquidity | $6,716.42 |
| Available Funds | $4,328.36 |
| Buying Power | $17,313.44 |
| SMA | $4,328.36 |

### Scenario 2: Leveraged at a Loss ($13K spent, stock fell from $650→$621.89)

| Metric | Value |
|--------|-------|
| Cash | -$3,000.00 |
| MVS | $12,437.80 |
| NLV | $9,437.80 |
| IM | $7,089.55 |
| MM | $4,104.47 |
| Excess Liquidity | $5,333.33 |
| Available Funds | $2,348.25 |
| Buying Power | $9,393.00 |
| SMA | $2,348.25 |

### Scenario 3: Multi-Asset Mixed Performance (QQQ gain + PLTR loss)

| Metric | Value |
|--------|-------|
| Cash | $4,600.00 |
| MVS (QQQ + PLTR) | $5,287.47 |
| NLV | $9,887.47 |
| IM | $3,013.86 |
| MM | $1,744.86 |
| Excess Liquidity | $8,142.61 |
| Available Funds | $6,873.61 |
| Buying Power | $27,494.44 |
| SMA | $6,873.61 |

## Key Files

- `apps/engine/execution/reg_t_validation.py` — Validation logic
- `apps/engine/execution/portfolio.py` — Portfolio class with Reg T metrics
- `apps/engine/tests/test_reg_t_validation.py` — Test suite
