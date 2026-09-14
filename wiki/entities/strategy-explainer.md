---
tags: [web, portfolio, ui, strategy]
category: entity
---

# Strategy Explainer

React component (`StrategyExplainer.tsx`) that renders a collapsible strategy description card on the portfolio detail page. Displays the thesis, entry rules, exit discipline, and academic grounding for system portfolios.

## Supported Strategies

- **`sys-smid-quality-compounder`** — Small/Mid-Cap Quality Compounder with Zero-Ceiling Invariant
- **`sys-sector-ls-consensus`** — Weekly Sector Long/Short Consensus Strategy
- **`sys-sector-uncorr-20d`** — 20-Day Uncorrelated Sector Momentum (Low-Beta Barbell)
- **`sys-sector-uncorr-7d`** — 7-Day Uncorrelated Sector Momentum (Weekly Rotation)
- **`sys-sector-naive-momentum`** — 20-Day Unconstrained Momentum (Top 2 Winners Benchmark Control)
- **`sys-sector-mean-reversion`** — 7-Day Sector Mean Reversion (Oversold Bounce)
- **`sys-daily-spy-*`** — Daily S&P 500 Intraday Trader

Returns `null` for non-system portfolios (e.g., individual LLM agents).

## Related

- [[entities/web-app]] — TanStack Start dashboard
- [[entities/smid-compounder]] — The SMID quality compounder system portfolio
- [[concepts/system-portfolios]] — Mechanical and quantitative benchmark strategies
- [[entities/sector-predictor-arena]] — Weekly sector ETF predictions and live rebalancing
