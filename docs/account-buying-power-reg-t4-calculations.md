This document serves as the comprehensive reference for **IBKR Reg T Margin Account** calculations. All scenarios assume an initial deposit of **$10,000 USD**.

---

## Core Calculation Rules

* **Net Liquidation Value (NLV):** 
* **Equity with Loan Value (ELV):** Same as NLV for marginable stocks.
* **Initial Margin (IM):**  (Reg T standard for new positions).
* **Maintenance Margin (MM):**  (Standard IBKR requirement).
* **Excess Liquidity:** 
* **Available Funds:** 
* **Buying Power (Intraday):** 
* **SMA (Simplified for Examples):** .

---

## Scenario 1: Near-Full Cash Allocation (No Leverage)

*The account uses almost all available cash to buy QQQ. No debt is incurred.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | $49.76 | $10,000 - $9,950.24 |
| **Market Value (MVS)** | $9,950.24 | 16 shares × $621.89 |
| **Equity (NLV)** | **$10,000.00** | $49.76 + $9,950.24 |
| **Initial Margin (IM)** | $4,975.12 | $9,950.24 × 50% |
| **Maint. Margin (MM)** | $2,487.56 | $9,950.24 × 25% |
| **Excess Liquidity** | $7,512.44 | $10,000 - $2,487.56 |
| **Available Funds** | $5,024.88 | $10,000 - $4,975.12 |
| **Buying Power** | $20,099.52 | $5,024.88 × 4 |
| **SMA** | $5,024.88 | $10,000 - $4,975.12 |

---

## Scenario 2: Profitable Leveraged Position

*The account spent $12,000 (borrowing $2,000). The stock price rose from $600 to $621.89.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$2,000.00 | $10,000 - (20 × $600) |
| **Market Value (MVS)** | $12,437.80 | 20 shares × $621.89 |
| **Equity (NLV)** | **$10,437.80** | -$2,000 + $12,437.80 |
| **Initial Margin (IM)** | $6,218.90 | $12,437.80 × 50% |
| **Maint. Margin (MM)** | $3,109.45 | $12,437.80 × 25% |
| **Excess Liquidity** | $7,328.35 | $10,437.80 - $3,109.45 |
| **Available Funds** | $4,218.90 | $10,437.80 - $6,218.90 |
| **Buying Power** | $16,875.60 | $4,218.90 × 4 |
| **SMA** | $4,437.80 | Higher of (Prior SMA or $10,437.8 - $6,000) |

---

## Scenario 3: Leveraged Position at a Loss

*The account spent $13,000 (borrowing $3,000). The stock price fell from $650 to $621.89.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$3,000.00 | $10,000 - (20 × $650) |
| **Market Value (MVS)** | $12,437.80 | 20 shares × $621.89 |
| **Equity (NLV)** | **$9,437.80** | -$3,000 + $12,437.80 |
| **Initial Margin (IM)** | $6,218.90 | $12,437.80 × 50% |
| **Maint. Margin (MM)** | $3,109.45 | $12,437.80 × 25% |
| **Excess Liquidity** | $6,328.35 | $9,437.80 - $3,109.45 |
| **Available Funds** | $3,218.90 | $9,437.80 - $6,218.90 |
| **Buying Power** | $12,875.60 | $3,218.90 × 4 |
| **SMA** | $3,500.00 | SMA doesn't drop with market loss unless IM increases |

---

## Scenario 4: Multi-Asset Portfolio (Mixed Performance)

*Holding 3 shares of QQQ (Gain) and 20 shares of PLTR (Loss).*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | $4,600.00 | $10k - ($1.8k + $3.6k) |
| **MVS (QQQ)** | $1,865.67 | 3 × $621.89 |
| **MVS (PLTR)** | $3,421.80 | 20 × $171.09 |
| **Total MVS** | $5,287.47 | $1,865.67 + $3,421.80 |
| **Equity (NLV)** | **$9,887.47** | $4,600 + $5,287.47 |
| **Initial Margin (IM)** | $2,643.74 | $5,287.47 × 50% |
| **Maint. Margin (MM)** | $1,321.87 | $5,287.47 × 25% |
| **Excess Liquidity** | $8,565.60 | $9,887.47 - $1,321.87 |
| **Available Funds** | $7,243.73 | $9,887.47 - $2,643.74 |
| **Buying Power** | $28,974.92 | $7,243.73 × 4 |
| **SMA** | $7,243.73 | Cash balance + Market cushion |

---

## Scenario 5: High Leverage (Approaching Reg T Limit)

*Buying $38,000 worth of stock with $10,000 cash. This uses 3.8x leverage.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$28,000.00 | $10,000 - $38,000 |
| **Market Value (MVS)** | $38,000.00 | - |
| **Equity (NLV)** | **$10,000.00** | -$28,000 + $38,000 |
| **Initial Margin (IM)** | $19,000.00 | $38,000 × 50% |
| **Maint. Margin (MM)** | $9,500.00 | $38,000 × 25% |
| **Excess Liquidity** | $500.00 | $10,000 - $9,500 |
| **Available Funds** | -$9,000.00 | $10,000 - $19,000 (Cannot open new trades) |
| **Buying Power** | $0.00 | Negative Available Funds = $0 BP |
| **SMA** | $0.00 | Reg T violation if held overnight |

---

## Scenario 6: Margin Call / Liquidation Trigger

*The $38,000 position from Scenario 5 drops by 5%.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$28,000.00 | Unchanged |
| **Market Value (MVS)** | $36,100.00 | $38,000 × 0.95 |
| **Equity (NLV)** | **$8,100.00** | -$28,000 + $36,100 |
| **Initial Margin (IM)** | $18,050.00 | $36,100 × 50% |
| **Maint. Margin (MM)** | $9,025.00 | $36,100 × 25% |
| **Excess Liquidity** | **-$925.00** | **CRITICAL: Liquidation likely** |
| **Available Funds** | -$9,950.00 | - |
| **Buying Power** | $0.00 | - |
| **SMA** | $0.00 | - |

