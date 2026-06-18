---
tags: [market-anomalies, empirical-finance, calendar-effects, structural-anomalies, factors]
category: concept
---

# Market Anomalies

Market anomalies and structural price distortions represent persistent, empirically verified deviations from the Efficient Market Hypothesis (EMH). These anomalies are caused by institutional trading schedules, psychological heuristics, or the mechanical plumbing constraints of financial institutions.

In the database, these are stored in the `memories` table as `ACADEMIC_PAPER` type. They have an importance score of `10` and are completely exempt from the tiered relevance decay model, ensuring they remain permanently available to the verifier agent via RAG (Retrieval-Augmented Generation) in `retrieve_for_decision()`.

---

## 1. Temporal & Calendar Anomalies

Temporal anomalies demonstrate that equity returns are mathematically concentrated during specific hours, days, or months due to institutional calendars and liquidity fluctuations.

### The Overnight Return Anomaly (The Night Effect)
* **Phenomenon:** The vast majority of historical net-positive market returns occur while the market is closed (between 4:00 PM and 9:30 AM EST). Intraday returns are historically flat or negative.
* **Root Cause:** Institutional execution preferences (trading intraday to ensure liquidity) versus information release timing (macro news and earnings released overnight).
* **Reference:** Lou, Polk, & Skouras (2019), *A tug of war: overnight versus intraday expected returns*, Journal of Financial Economics.
* **Actionable Application:** Buying close to the market close (3:55 PM EST) and exiting near the open (9:30 AM EST) to capture the night premium.

### The Turn-of-the-Month Effect
* **Phenomenon:** Disproportionately high market returns occur precisely on the last trading day of the month and the first three days of the new month. The rest of the month's average return is historically effectively zero.
* **Root Cause:** Structural capital inflows hitting the market simultaneously, including 401(k) allocations, bi-weekly payrolls, and institutional portfolio rebalancing.
* **Reference:** McConnell & Xu (2008), *Equity Returns at the Turn of the Month*, Financial Analysts Journal.
* **Actionable Application:** Concentrating long equity exposure around the four-day turn-of-the-month window and holding cash or market-neutral positions during the middle of the month.

### The Pre-Holiday Liquidity Vacuum
* **Phenomenon:** The single trading day immediately preceding a major market holiday (like July 4th or Christmas) generates returns up to 14 times higher than standard trading days.
* **Root Cause:** Short-sellers covering positions to avoid unhedgeable weekend/holiday risk, combined with a general liquidity vacuum as institutional traders leave the desks early.
* **Reference:** Ariel (1990), *High Stock Returns before Holidays: Existence and Evidence on Possible Causes*, Journal of Finance.
* **Actionable Application:** Maintaining a long equity bias on the trading day before major US market holidays.

### The January Effect
* **Phenomenon:** Small-cap stocks historically exhibit outsized positive returns during the month of January compared to large-caps.
* **Root Cause:** Tax-loss harvesting. Investors dump losing stocks in December for tax write-offs, temporarily depressing their prices, and capital floods back into these discounted equities in January.
* **Reference:** Rozeff & Kinney (1976), *Capital Market Seasonality: The Case of Stock Returns*, Journal of Financial Economics.
* **Actionable Application:** Buying beaten-down small-caps in mid-to-late December and selling them in mid-January (though noting this anomaly has degraded in modern markets due to crowded arbitrage).

### The Weekend Effect / Monday Effect
* **Phenomenon:** Historically, stock returns on Mondays were significantly lower (often negative) compared to the preceding Fridays.
* **Root Cause:** Companies traditionally delayed releasing bad news until Friday night after the close, leading to a delayed sell-off on Monday morning. Algorithmic trading has largely eliminated this.
* **Reference:** French (1980), *Stock Returns and the Weekend Effect*, Journal of Financial Economics.
* **Actionable Application:** Adjusting Monday morning execution and sentiment targets to account for weekend news accumulation, while remaining cautious of legacy bias.

---

## 2. Information & Event-Driven Anomalies

Event-driven anomalies occur due to human cognitive failures. The EMH assumes news is priced in instantly; these effects prove human anchoring and anticipation stretch these events into multi-day trends.

### Post-Earnings-Announcement Drift (PEAD)
* **Phenomenon:** When a company announces a severe earnings surprise (positive or negative), the stock price does not immediately adjust to its final fair value. Instead, it slowly "drifts" in the direction of the surprise for up to 60 days.
* **Root Cause:** Human behavioral underreaction. Analysts and investors anchor to their prior valuation models and are psychologically slow to fully accept and price in the new reality.
* **Reference:** Bernard & Thomas (1989), *Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?*, Journal of Accounting Research.
* **Actionable Application:** Entering long positions in stocks with massive positive earnings surprises (and shorting negative surprises) and holding them for a multi-week horizon.

### Pre-FOMC Announcement Drift
* **Phenomenon:** The US equity market experiences statistically massive excess returns in the precise 24-hour window *before* the Federal Reserve announces its interest rate decisions.
* **Root Cause:** Institutional de-risking. As major funds close out short positions and hedge against uncertainty before the announcement, the mechanical buying pressure pushes the index upward in an informational vacuum.
* **Reference:** Lucca & Moench (2015), *The Pre-FOMC Announcement Drift*, Journal of Finance.
* **Actionable Application:** Initiating a long position on broad market indices (e.g., SPY) 24 hours prior to scheduled FOMC announcements and exiting immediately before the official release.

---

## 3. Structural & Plumbing Anomalies

Structural anomalies occur because the market is a physical machine with rigid rules. Prices move because participants are contractually, legally, or mathematically forced to trade.

### The Index Inclusion Effect (The Passive Squeeze)
* **Phenomenon:** A stock experiences severe price volatility and historically upward pressure simply because it is announced that it will be added to a major index (like the S&P 500).
* **Root Cause:** The legal mandate of passive ETFs and index-tracking funds, which are contractually obligated to buy the stock regardless of its current valuation, allowing quantitative funds to front-run the trade and squeeze the price.
* **Reference:** Shleifer (1986), *Do Demand Curves for Stocks Slope Down?*, Journal of Finance.
* **Actionable Application:** Buying a stock immediately upon the announcement of its inclusion in a major index and selling to the passive index funds on the actual effective date of inclusion.

### Options Expiration Pinning (Max Pain)
* **Phenomenon:** On major options expiration dates (historically the third Friday of the month), highly traded stocks statistically cluster and close exactly on strike prices ending in $0 or $5.
* **Root Cause:** Market Maker Delta Hedging. To remain risk-neutral, massive financial institutions mathematically hedge their options books by buying and selling the underlying stock, artificially pinning the stock to the strike price where the most options expire worthless.
* **Reference:** Ni, Pearson, & Poteshman (2005), *Stock Price Clustering on Option Expiration Dates*, Journal of Financial Economics.
* **Actionable Application:** Designing reversal or range-bound strategies on OPEX day targeting key option strikes, and avoiding breakout trades on highly optioned stocks on the third Friday of the month.

---

## 4. Academic Risk Premia (The Factors)

Strategic factor exposures provide true structural risk premiums that systematically outperform standard market-cap-weighted indices over multi-decade timelines.

### Fama-French Multi-Factor Model
* **Phenomenon:** Standard market beta is insufficient to explain stock returns. Portfolios tilted toward Value, Size, Profitability, and Investment systematically outperform.
* **Root Causes:** 
  * **Value (HML):** Low price-to-book stocks outperform high-growth glamour stocks (rational compensation for distress risk and behavioral extrapolation).
  * **Size (SMB):** Small-cap stocks outperform large-caps (compensation for systemic distress and liquidity risk).
  * **Profitability (RMW):** Companies with high operating profitability outperform weak ones (robust cash flows).
  * **Investment (CMA):** Companies with conservative asset growth outperform aggressive spenders (avoiding value-destroying empire building).
* **Reference:** Fama & French (2015), *A Five-Factor Asset Pricing Model*, Journal of Financial Economics.
* **Actionable Application:** Systematic portfolio tilts prioritizing high-profitability, conservative-spending value companies.

### The Momentum Anomaly
* **Phenomenon:** Assets that have gone up over the last 3 to 12 months are statistically highly likely to keep going up in the near future, and losers keep losing.
* **Root Cause:** A blend of PEAD (slow adjustment to fundamentals), institutional herd behavior, and fund flow mechanics.
* **Reference:** Jegadeesh & Titman (1993), *Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency*, Journal of Finance.
* **Actionable Application:** Deploying cross-sectional momentum filters (buying the top decile of 6-to-12-month performers and rebalancing monthly).

---

## RAG Integration

These anomalies are seeded into the Supabase database via `seed_academic_papers.py`. Because they are defined as `ACADEMIC_PAPER` memory types, they are excluded from the decay logic in `decay_memories()`. This ensures that they are permanently indexed in the vector database and can be retrieved by agents to ground their trading thesis.

## Related

* [[entities/academic-paper-seeding]] — The database seeding script
* [[concepts/rag-strategy]] — Tiered context injection and per-agent RAG
* [[concepts/reasoning]] — Parallel LLM analysis with tool-calling loops
