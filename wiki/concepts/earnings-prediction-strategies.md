---
tags: [earnings, pead, revision-momentum, bellwethers, fundamental-analysis, alpha-strategies]
category: concept
---

# Earnings Alpha Strategies

Quantitative and event-driven methodologies for trading corporate earnings across single stocks, sectors, and index aggregates without relying on unfeasible penny-EPS guessing.

## Overview & Pitfalls of Naive EPS Forecasting

Predicting raw quarterly Earnings Per Share (EPS) faces severe headwinds:
1. **The Guidance Trap**: Past earnings are sunk; equity valuation is the discounted sum of future cash flows. A 20% EPS beat accompanied by a -2% next-quarter guidance revision typically results in immediate sell-offs.
2. **The Whisper Gap**: Official sell-side consensus is routinely lowballed by management. Buy-side desks trade against elevated whisper numbers.
3. **Volatility Crush**: Holding options through earnings suffers from severe post-announcement implied volatility (IV) collapse.
4. **The Accrual Anomaly**: High GAAP net income driven by working capital expansion (non-cash accruals) underperforms cash-generative earnings over 2 to 4 quarters (Sloan 1996).

To build sustainable edge, systematic architectures exploit structural market underreactions and cross-asset information diffusion.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EARNINGS ALPHA STRATEGY PIPELINE                     │
└─────────────────────────────────────────────────────────────────────────┘
   │
   ├─► Pre-Earnings / Year-Round: Strategy 2 (Revision Velocity & Breadth)
   │   └─ Track sell-side herd upgrades and upward estimate acceleration
   │
   ├─► Earnings Season (Early Wave): Strategy 3 (Bellwether Spillovers)
   │   └─ LLM transcript analysis on early reporters to front-run peers
   │
   └─► Post-Earnings (Execution): Strategy 1 (Post-Earnings Drift / PEAD)
       └─ Capture 10-45 day institutional accumulation post top-decile SUE
```

---

## Strategy 1: Post-Earnings Announcement Drift (PEAD)

First documented by Ball & Brown (1968), PEAD describes the empirical phenomenon where stock prices continue drifting in the direction of an earnings surprise for 15 to 60 trading days post-announcement.

### Quantitative Formulation: Standardized Unexpected Earnings (SUE)

$$\text{SUE}_t = \frac{\text{Actual EPS}_t - \text{Consensus EPS}_t}{\sigma(\text{Surprise History})}$$

* $\sigma(\text{Surprise History})$: Sample standard deviation of earnings surprises over the trailing 8 quarters.
* Entry Criteria: Top-decile $\text{SUE} \ge +2.0$, positive revenue surprise, and no pre-announcement parabolic run-up (> 25% in 20 days).
* Holding Period: 10 to 45 trading days, managed via ATR trailing stops.

### Structural Drivers
- **Institutional Execution Friction**: Large asset managers execute block orders via TWAP/VWAP over multi-week horizons to minimize market impact.
- **Disposition Effect**: Retail profit-taking on Day 1 temporarily caps initial gaps, creating post-event drift as institutional buying absorbs float.

---

## Strategy 2: Earnings Revision Velocity & Breadth

Exploits sell-side analyst herding behavior. When one lead analyst updates an earnings model upward, peer analysts systematically follow over the subsequent 2 to 4 weeks to mitigate career risk.

### Quantitative Metrics

1. **Revision Breadth (30-Day Window)**:
$$\text{Revision Breadth}_{30d} = \frac{N_{\text{up}} - N_{\text{down}}}{N_{\text{total}}}$$

* Filter threshold: $\text{Revision Breadth} \ge +0.60$ with a minimum analyst coverage $N_{\text{total}} \ge 6$.

2. **Revision Velocity**:
$$\text{Revision Velocity} = \frac{\text{Consensus EPS}_t - \text{Consensus EPS}_{t-30d}}{\text{Stock Price}_t}$$

### Structural Drivers
- Continuous 365-day signal (independent of earnings calendar peaks).
- Leads actual reported earnings surprises by 30 to 60 days.

---

## Strategy 3: Bellwether & Supply Chain Spillovers

Earnings season follows a chronological cadence. Upstream foundries, large money-center banks, and freight carriers report 1 to 3 weeks before downstream tech designers, regional banks, and consumer retailers.

### Quantitative & LLM Pipeline

1. **Sector Margin Surprise Diffusion**:
$$\Delta \text{Sector Margin} = \frac{1}{K} \sum_{k=1}^K (\text{Reported Operating Margin}_k - \text{Expected Operating Margin}_k)$$

2. **LLM Transcript Intelligence**:
   - Ingest 10-Q and earnings call transcripts of early bellwethers (e.g. TSMC, FedEx, JPMorgan).
   - Extract structured risk tags: `supplier_lead_time_change`, `regional_demand_weakness`, `pricing_power_decay`.
   - Update predictive stance on late-reporting peers before their earnings date.

---

## Strategy Comparison Matrix

| Dimension | Strategy 1: PEAD | Strategy 2: Revision Velocity | Strategy 3: Bellwether Spillovers |
| :--- | :--- | :--- | :--- |
| **Holding Horizon** | 10 to 45 Days | 20 to 90 Days | 3 to 14 Days |
| **Timing** | Post-announcement | Continuous | Clustered (Weeks 2-5 of quarter) |
| **Overnight Risk** | Low (enters post-gap) | Moderate | High (holds into unannounced print) |
| **Primary Data Source** | FMP actual vs expected EPS | Historical analyst consensus series | Earnings calendar, transcripts, sector graphs |
| **LLM Agent Role** | Low (numeric calculations) | Low to Medium | High (call transcript reasoning) |

---

## Related

- [[concepts/fundamental-analysis]]
- [[concepts/market-anomalies]]
- [[entities/sector-predictor-arena]]
- [[entities/market-barometer-audit]]
- [[concepts/magnitude-calibration]]
