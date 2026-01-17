This document serves as the comprehensive reference for **Reg-T Margin Account** calculations. It simulates how Interactive Brokers (IBKR) tracks a $10,000 portfolio across various market conditions, including leverage and losses.

---

## Core Calculation Reference

| Metric | Calculation Formula |
| --- | --- |
| **Total Stock Value (SV)** |  |
| **Net Liquidation Value (NLV)** |  |
| **Equity with Loan Value (ELV)** |  |
| **Initial Margin (IM)** |  (Intraday) |
| **Maintenance Margin (MM)** |  |
| **Current Available Funds** |  |
| **Excess Liquidity** |  |
| **Buying Power (Intraday)** |  |

---

## Scenario 1: Basic Cash-Backed Purchase (No Leverage)

The account uses almost all initial cash but does not borrow.

* **Initial Cash:** $10,000
* **Action:** Buy 16 shares of QQQ @ $621.89 ($9,950.24 total)

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | $49.76 | $10,000 - $9,950.24 |
| **Stock Value** | $9,950.24 | 16 \times $621.89 |
| **Equity (NLV)** | **$10,000.00** | $49.76 + $9,950.24 |
| **Initial Margin** | $2,487.56 |  |
| **Maint. Margin** | $2,487.56 |  |
| **Available Funds** | $7,512.44 | $10,000 - $2,487.56 |
| **Excess Liquidity** | $7,512.44 | $10,000 - $2,487.56 |
| **Buying Power** | **$30,049.76** |  |

---

## Scenario 2: Leveraged Position (Profitable)

The account borrows cash to buy more stock than it has on hand.

* **Initial Cash:** $10,000
* **Action:** Buy 20 shares QQQ @ $600 ($12,000 total). **Current Price:** $621.89.

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$2,000.00 | $10,000 - $12,000 |
| **Stock Value** | $12,437.80 | 20 \times $621.89 |
| **Equity (NLV)** | **$10,437.80** | -$2,000 + $12,437.80 |
| **Initial Margin** | $3,109.45 |  |
| **Maint. Margin** | $3,109.45 |  |
| **Available Funds** | $7,328.35 | $10,437.80 - $3,109.45 |
| **Excess Liquidity** | $7,328.35 | $10,437.80 - $3,109.45 |
| **Buying Power** | **$29,313.40** |  |

---

## Scenario 3: Leveraged Position (Unrealized Loss)

The account is borrowing, and the price has dropped below cost basis.

* **Initial Cash:** $10,000
* **Action:** Buy 20 shares QQQ @ $650 ($13,000 total). **Current Price:** $621.89.

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$3,000.00 | $10,000 - $13,000 |
| **Stock Value** | $12,437.80 | 20 \times $621.89 |
| **Equity (NLV)** | **$9,437.80** | -$3,000 + $12,437.80 |
| **Initial Margin** | $3,109.45 |  |
| **Maint. Margin** | $3,109.45 |  |
| **Available Funds** | $6,328.35 | $9,437.80 - $3,109.45 |
| **Excess Liquidity** | $6,328.35 | $9,437.80 - $3,109.45 |
| **Buying Power** | **$25,313.40** |  |

---

## Scenario 4: Multi-Asset Portfolio (Mixed Performance)

Tracking multiple tickers with varying gains and losses.

* **Initial Cash:** $10,000
* **Positions:** * 3 shares QQQ @ $600 (Current $621.89) = $1,865.67
* 20 shares PLTR @ $180 (Current $171.09) = $3,421.80


* **Total Spend:** $1,800 + $3,600 = $5,400.

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | $4,600.00 | $10,000 - $5,400 |
| **Stock Value** | $5,287.47 | $1,865.67 (QQQ) + $3,421.80 (PLTR) |
| **Equity (NLV)** | **$9,887.47** | $4,600 + $5,287.47 |
| **Initial Margin** | $1,321.87 |  |
| **Maint. Margin** | $1,321.87 |  |
| **Available Funds** | $8,565.60 | $9,887.47 - $1,321.87 |
| **Excess Liquidity** | $8,565.60 | $9,887.47 - $1,321.87 |
| **Buying Power** | **$34,262.40** |  |

---

## Scenario 5: High Leverage / Boundary Test (Near Liquidation)

An agent uses 3.8x leverage, and the market drops.

* **Initial Cash:** $10,000
* **Action:** Buy $38,000 worth of stock. (Borrowed $28,000).
* **Market Drop:** Stock value drops 20% to $30,400.

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$28,000.00 | $10,000 - $38,000 |
| **Stock Value** | $30,400.00 | Market value after drop |
| **Equity (NLV)** | **$2,400.00** | -$28,000 + $30,400 |
| **Initial Margin** | $7,600.00 |  |
| **Maint. Margin** | $7,600.00 |  |
| **Available Funds** | -$5,200.00 | **REJECT NEW TRADES** ($2,400 - $7,600) |
| **Excess Liquidity** | -$5,200.00 | **LIQUIDATION TRIGGERED** ($2,400 - $7,600) |
| **Buying Power** | **$0.00** | Cannot buy with negative liquidity |

---

## Scenario 6: Maximum Buying Power Utilization

An account attempting to use the full 4x leverage.

* **Initial Cash:** $10,000.
* **Action:** Buy $40,000 of stock.

| Metric | Value | Calculation |
| --- | --- | --- |
| **Cash** | -$30,000.00 | $10,000 - $40,000 |
| **Stock Value** | $40,000.00 | Market Value |
| **Equity (NLV)** | **$10,000.00** | -$30,000 + $40,000 |
| **Initial Margin** | $10,000.00 |  |
| **Maint. Margin** | $10,000.00 |  |
| **Available Funds** | **$0.00** | $10,000 - $10,000 |
| **Excess Liquidity** | $0.00 | $10,000 - $10,000 |
| **Buying Power** | **$0.00** | Account is fully maxed out |

Would you like me to create a **Python class** that takes these scenarios as inputs and returns the calculated table values?