This document serves as the comprehensive reference for **IBKR Reg T Margin Account** calculations. All scenarios assume an initial deposit of **$10,000 USD**.

---

## Core Calculation Rules

* **Net Liquidation Value (NLV):** `Cash + Market Value of Securities`
* **Realized Value:** `Cash + Total Cost Basis of Positions`. Effectively NLV excluding unrealized Profit/Loss.
* **Equity with Loan Value (ELV):** Same as NLV for marginable stocks.
* **Initial Margin (IM):** `MVS × 57%` (Reg T standard for new positions).
* **Maintenance Margin (MM):** `MVS × 33%` (Standard IBKR requirement).
* **Excess Liquidity:** `NLV - Maintenance Margin`
* **Available Funds:** `NLV - Initial Margin`
* **Buying Power (Intraday):** `Available Funds × 4`
* **SMA (Simplified for Examples):** `Max(Previous SMA, NLV - (MVS × 0.57))`.

---

## Scenario 1: Near-Full Cash Allocation (No Leverage)

*Buying $9,950.24 of QQQ with $10,000 cash.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | $49.76 | $10,000 - $9,950.24 |
| **Market Value (MVS)** | $9,950.24 | 16 shares × $621.89 |
| **Equity (NLV)** | **$10,000.00** | $49.76 + $9,950.24 |
| **Realized** | **$10,000.00** | $49.76 + $9,950.24 (Cost Basis) |
| **Initial Margin (IM)** | $5,671.64 | $9,950.24 × 57% |
| **Maint. Margin (MM)** | $3,283.58 | $9,950.24 × 33% |
| **Excess Liquidity** | $6,716.42 | $10,000 - $3,283.58 |
| **Available Funds** | $4,328.36 | $10,000 - $5,671.64 |
| **Buying Power** | $17,313.44 | $4,328.36 × 4 |
| **SMA** | $4,328.36 | $10,000 - $5,671.64 |

---

## Scenario 2: Leveraged Position (3.8x Leverage)

*Buying $38,000 worth of stock with $10,000 cash.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$28,000.00 | $10,000 - $38,000 |
| **Market Value (MVS)** | $38,000.00 | — |
| **Equity (NLV)** | **$10,000.00** | -$28,000 + $38,000 |
| **Realized** | **$10,000.00** | -$28,000 + $38,000 (Cost Basis) |
| **Initial Margin (IM)** | $21,660.00 | $38,000 × 57% |
| **Maint. Margin (MM)** | $12,540.00 | $38,000 × 33% |
| **Excess Liquidity** | -$2,540.00 | **IMMEDIATE LIQUIDATION** |
| **Available Funds** | -$11,660.00 | $10,000 - $21,660 |
| **Buying Power** | $0.00 | Cannot open new positions |
| **SMA** | -$11,660.00 | Reg T violation |

---

## Scenario 3: Leveraged Position at a Loss

*The account spent $13,000 (borrowing $3,000). The stock price fell from $650 to $621.89.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$3,000.00 | $10,000 - (20 × $650) |
| **Market Value (MVS)** | $12,437.80 | 20 shares × $621.89 |
| **Equity (NLV)** | **$9,437.80** | -$3,000 + $12,437.80 |
| **Realized** | **$10,000.00** | -$3,000 + $13,000 (Cost Basis) |
| **Initial Margin (IM)** | $7,089.55 | $12,437.80 × 57% |
| **Maint. Margin (MM)** | $4,104.47 | $12,437.80 × 33% |
| **Excess Liquidity** | $5,333.33 | $9,437.80 - $4,104.47 |
| **Available Funds** | $2,348.25 | $9,437.80 - $7,089.55 |
| **Buying Power** | $9,393.00 | $2,348.25 × 4 |
| **SMA** | $2,348.25 | SMA doesn't drop with market loss unless IM increases |

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
| **Realized** | **$10,000.00** | $4,600 + ($1,800 + $3,600) |
| **Initial Margin (IM)** | $3,013.86 | $5,287.47 × 57% |
| **Maint. Margin (MM)** | $1,744.86 | $5,287.47 × 33% |
| **Excess Liquidity** | $8,142.61 | $9,887.47 - $1,744.86 |
| **Available Funds** | $6,873.61 | $9,887.47 - $3,013.86 |
| **Buying Power** | $27,494.44 | $6,873.61 × 4 |
| **SMA** | $6,873.61 | Cash balance + Market cushion |

---

## Scenario 5: High Leverage (Approaching Reg T Limit)

*Buying $38,000 worth of stock with $10,000 cash. This uses 3.8x leverage.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$28,000.00 | $10,000 - $38,000 |
| **Market Value (MVS)** | $38,000.00 | — |
| **Equity (NLV)** | **$10,000.00** | -$28,000 + $38,000 |
| **Realized** | **$10,000.00** | -$28,000 + $38,000 (Cost) |
| **Initial Margin (IM)** | $21,660.00 | $38,000 × 57% |
| **Maint. Margin (MM)** | $12,540.00 | $38,000 × 33% |
| **Excess Liquidity** | -$2,540.00 | $10,000 - $12,540 (Reg T violation) |
| **Available Funds** | -$11,660.00 | $10,000 - $21,660 (Cannot open new trades) |
| **Buying Power** | $0.00 | Negative Available Funds = $0 BP |
| **SMA** | -$11,660.00 | Immediate liquidation required |

---

## Scenario 6: Margin Call / Liquidation Trigger

*The $38,000 position from Scenario 5 drops by 5%.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$28,000.00 | Unchanged |
| **Market Value (MVS)** | $36,100.00 | $38,000 × 0.95 |
| **Equity (NLV)** | **$8,100.00** | -$28,000 + $36,100 |
| **Realized** | **$10,000.00** | -$28,000 + $38,000 (Cost) |
| **Initial Margin (IM)** | $20,577.00 | $36,100 × 57% |
| **Maint. Margin (MM)** | $11,913.00 | $36,100 × 33% |
| **Excess Liquidity** | **-$3,813.00** | **CRITICAL: Liquidation required** |
| **Available Funds** | -$12,477.00 | — |
| **Buying Power** | $0.00 | — |
| **SMA** | -$12,477.00 | — |


## Scenario 7: Portfolio Snapshot

*Based on equity of $194,700 and specific holdings.*

| Metric | Calculation | Value |
| --- | --- | --- |
| **Net Market Value** | All long/short positions | $245,651.99 |
| **Gross Exposure** | Total gross value of positions | $316,179.99 |
| **Cash Balance** | $194,700 - $245,651.99 | -$50,951.99 |
| **Maintenance Margin** | $316,179.99 × 0.33 | $104,339.40 |
| **Excess Liquidity** | $194,700 - $104,339.40 | $90,360.60 |
| **SMA** | $194,700 - ($316,179.99 × 0.57) | $14,477.41 |
| **Realized** | Cash + Total Cost Basis | *Variable* |
| **Buying Power** | $14,477.41 × 4 | $57,909.64 |

---

## Scenario 8: Trade Closure with Realized P/L

*Based on a $10,000 account closing a trade with a $1,000 profit. No other positions held.*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | $11,000.00 | $10,000 (Initial) + $1,000 (Profit) |
| **Market Value (MVS)** | $0.00 | No open positions |
| **Equity (NLV)** | **$11,000.00** | $11,000 (Cash) + $0 (MVS) |
| **Realized** | **$11,000.00** | Cash + Cost Basis ($0) |
| **Initial Margin (IM)** | $0.00 | $0 × 57% |
| **Maint. Margin (MM)** | $0.00 | $0 × 33% |
| **Excess Liquidity** | $11,000.00 | $11,000 - $0 |
| **Available Funds** | $11,000.00 | $11,000 - $0 |
| **Buying Power** | $44,000.00 | $11,000 × 4 |
| **SMA** | $11,000.00 | $11,000 - ($0 × 0.57) |

---

## Scenario 9: Portfolio Snapshot with Historical Loss

*Holding 3 shares of QQQ (Value: $1,865.67) and 20 shares of PLTR (Value: $3,421.80). Account started at $10,000 but lost $1,000 on a past trade (Realized Value = $9,000).*

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | $3,712.53 | $9,000 (Realized) - ($1,800 + $3,487.47 Cost Basis*) |
| **MVS (QQQ)** | $1,865.67 | 3 × $621.89 |
| **MVS (PLTR)** | $3,421.80 | 20 × $171.09 |
| **Total MVS** | $5,287.47 | $1,865.67 + $3,421.80 |
| **Equity (NLV)** | **$9,000.00** | $3,712.53 (Cash) + $5,287.47 (MVS) |
| **Realized** | **$9,000.00** | Current Cash + Position Cost Basis |
| **Initial Margin (IM)** | $3,013.86 | $5,287.47 × 57% |
| **Maint. Margin (MM)** | $1,744.86 | $5,287.47 × 33% |
| **Excess Liquidity** | $7,255.14 | $9,000 - $1,744.86 |
| **Available Funds** | $5,986.14 | $9,000 - $3,013.86 |
| **Buying Power** | $23,944.56 | $5,986.14 × 4 |
| **SMA** | $5,986.14 | $9,000 - ($5,287.47 × 0.57) |

**Note: In Scenario 9, the NLV reflects the total account value after the $1,000 loss was realized. The "Realized" row tracks your equity excluding current unrealized fluctuations.*

---

### Understanding the SMA Impact

In **Scenario 9**, even though you have a "gain" on QQQ, your overall SMA is lower than Scenario 4 because your starting "Realized" equity was reduced by the previous $1,000 loss. SMA effectively tracks your **Buying Power "High Water Mark"** adjusted for cash movements and Reg T requirements.
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
* *Formula:* `Market Value of Securities (MVS) × 57.0%` (for most marginable stocks)


* **Maintenance Margin (MM):** The equity required to keep a position open.
* *Formula:* `Market Value of Securities (MVS) × 33.0%` (Standard IBKR house requirement; may be higher for volatile stocks)



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
* `Equity with Loan Value (ELV) - Reg T Margin (57% of Market Value)`



### Critical SMA Constraints:

* **The "No-Loss" Rule:** SMA does **not** decrease simply because the market price of your stocks goes down. It only decreases through withdrawals or new purchases.
* **Market Gains:** If the stock price rises, the SMA increases at the end of the day if `(ELV - 57% MVS)` is greater than the current SMA.
* **EOD Requirement:** At the close of the US trading day (15:50–17:20 ET), the SMA balance must be **≥ 0**. If it is negative, IBKR will liquidate positions to bring the account into compliance.

---

## Applied Formula Summary Table

| Metric | Technical Formula | Purpose |
| --- | --- | --- |
| **Cash** | `Initial Deposit - (Shares × Purchase Price)` | Actual currency balance (Negative = Debt) |
| **NLV** | `Cash + Market Value of Securities` | Total account liquidation value |
| **IM** | `MVS × 0.57` | Reg T cost to open a position |
| **MM** | `MVS × 0.33` | Min. equity to avoid liquidation |
| **Excess Liquidity** | `NLV - MM` | Safety margin for existing positions |
| **Realized** | `Cash + Total Cost Basis` | Account value without unrealized P/L |
| **Available Funds** | `NLV - IM` | Capacity for new trades |
| **Buying Power** | `Available Funds × 4` | Intraday purchase capacity |
| **SMA** | `Max(Prior SMA + ∆Cash - IM_trades, NLV - (MVS × 0.57))` | Reg T credit line / Overnight compliance |

### Example Walkthrough (Scenario 3 Logic)

* **Initial SMA:** $10,000 (Initial deposit)
* **Trade:** Buy $12,000 of stock.
* **SMA Change:** SMA decreases by Initial Margin ($12,000 × 0.57 = $6,840). New SMA = **$3,160**.
* **Market Rise:** Stock rises to $12,437.80.
* **End of Day Check:** `ELV ($10,437.80) - 57% MVS ($7,089.55) = $3,348.25`.
* **Result:** Since $3,348.25 is higher than the existing $3,160, the **SMA is updated to $3,348.25**.

---