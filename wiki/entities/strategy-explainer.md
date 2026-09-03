---
tags: [web, portfolio, ui, strategy]
category: entity
---

# Strategy Explainer

React component (`StrategyExplainer.tsx`) that renders a collapsible strategy description card on the portfolio detail page. Displays the thesis, entry rules, exit discipline, and academic grounding for system portfolios.

## Supported Strategies

- **`sys-smid-quality-compounder`** — Small/Mid-Cap Quality Compounder with Zero-Ceiling Invariant
- **`sys-sector-ls-consensus`** — Weekly Sector Long/Short Consensus Strategy
- **`sys-daily-spy-*`** — Daily S&P 500 Intraday Trader

Returns `null` for non-system portfolios (e.g., individual LLM agents).

## Related

- [[entities/web-app]] — TanStack Start dashboard
- [[entities/smid-compounder]] — The SMID quality compounder system portfolio
