This document serves as the comprehensive reference for **IBKR Reg T Margin Account** calculations. All scenarios assume an initial deposit of **$10,000 USD**.

---

## Core Calculation Rules

* **Net Liquidation Value (NLV):** `Cash + Market Value of Securities`
* **Equity with Loan Value (ELV):** Same as NLV for marginable stocks.
* **Initial Margin (IM):** `MVS × 50%` (Reg T standard for new positions).
* **Maintenance Margin (MM):** `MVS × 25%` (Standard IBKR requirement).
* **Excess Liquidity:** `NLV - Maintenance Margin`
* **Available Funds:** `NLV - Initial Margin`
* **Buying Power (Intraday):** `Available Funds × 4`
* **SMA (Simplified for Examples):** `Max(Previous SMA, NLV - IM)`.

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

----------
# Calculations:
This document provides the technical formulas for an **Interactive Brokers (IBKR) Reg T Margin Account**, specifically defining the logic used in the Special Memorandum Account (SMA) and related margin metrics.

---

## Technical Reference: IBKR Reg T Margin Formulas

### 1. Fundamental Equity Metrics

* **Net Liquidation Value (NLV):** Total value of assets if liquidated at current market price.
* *Formula:* `Cash + Stock Value + Options Value + Bond Value + Fund Value + Accrued Interest/Dividends`


* **Equity with Loan Value (ELV):** The value of the account available to be used as collateral for a margin loan.
* *Formula:* `Total Cash Value + Stock Value + Bond Value + Fund Value + (European/Asian Options Value)`
* *Note:* For standard marginable US stocks, **ELV = NLV**. US stock options generally have no loan value.



### 2. Margin Requirements

* **Initial Margin (IM):** The equity required to open a new position (Regulation T standard).
* *Formula:* `Market Value of Securities (MVS) × 50.0%` (for most marginable stocks)


* **Maintenance Margin (MM):** The equity required to keep a position open.
* *Formula:* `Market Value of Securities (MVS) × 25.0%` (Standard IBKR house requirement; may be higher for volatile stocks)



### 3. Real-Time Trading Metrics

* **Available Funds:** The amount available to open *new* positions.
* *Formula:* `Equity with Loan Value (ELV) - Initial Margin (IM)`


* **Excess Liquidity:** The "cushion" before liquidation occurs.
* *Formula:* `Equity with Loan Value (ELV) - Maintenance Margin (MM)`


* **Buying Power (Intraday):** The maximum dollar amount of stock you can purchase.
* *Formula:* `Available Funds × 4` (Assumes a 25% intraday initial margin; note that this reverts to 2x at the end of the day based on Reg T 50% IM).



---

## 4. Special Memorandum Account (SMA)

The SMA is a "line of credit" representing the excess equity in a margin account. It is a **memorandum account**, meaning it does not reflect actual cash but rather the maximum amount you could withdraw or use for further purchases.

### Core SMA Calculation Rules:

IBKR calculates SMA as the **Greater** of the following two values:

1. **Market-Driven SMA:**
* `Prior Day SMA +/- Change in Day's Cash +/- Today's Trades Initial Margin Requirements`
* *Note:* Cash increases (deposits/dividends) increase SMA 1:1. Buying stock reduces SMA by the 50% IM requirement.


2. **Equity-Driven SMA (End of Day):**
* `Equity with Loan Value (ELV) - Reg T Margin (50% of Market Value)`



### Critical SMA Constraints:

* **The "No-Loss" Rule:** SMA does **not** decrease simply because the market price of your stocks goes down. It only decreases through withdrawals or new purchases.
* **Market Gains:** If the stock price rises, the SMA increases at the end of the day if `(ELV - 50% MVS)` is greater than the current SMA.
* **EOD Requirement:** At the close of the US trading day (15:50–17:20 ET), the SMA balance must be **≥ 0**. If it is negative, IBKR will liquidate positions to bring the account into compliance.

---

## Applied Formula Summary Table

| Metric | Technical Formula | Purpose |
| --- | --- | --- |
| **Cash** | `Initial Deposit - (Shares × Purchase Price)` | Actual currency balance (Negative = Debt) |
| **NLV** | `Cash + Market Value of Securities` | Total account liquidation value |
| **IM** | `MVS × 0.50` | Reg T cost to open a position |
| **MM** | `MVS × 0.25` | Min. equity to avoid liquidation |
| **Excess Liquidity** | `NLV - MM` | Safety margin for existing positions |
| **Available Funds** | `NLV - IM` | Capacity for new trades |
| **Buying Power** | `Available Funds × 4` | Intraday purchase capacity |
| **SMA** | `Max(Prior SMA + ∆Cash - IM_trades, NLV - (MVS × 0.50))` | Reg T credit line / Overnight compliance |

### Example Walkthrough (Scenario 2 Logic)

* **Initial SMA:** $10,000 (Initial deposit)
* **Trade:** Buy $12,000 of stock.
* **SMA Change:** SMA decreases by Initial Margin ($6,000). New SMA = **$4,000**.
* **Market Rise:** Stock rises to $12,437.80.
* **End of Day Check:** `ELV ($10,437.80) - 50% MVS ($6,218.90) = $4,218.90`.
* **Result:** Since $4,218.90 is higher than the existing $4,000, the **SMA is updated to $4,218.90**.